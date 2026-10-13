from datetime import datetime, timedelta, timezone

T0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


def test_empty_library(client):
    res = client.get("/api/v1/books")
    assert res.status_code == 200
    assert res.json() == {"items": [], "page": 1, "size": 20, "total": 0}


def test_lists_books_newest_first(client, make_user, make_book):
    user = make_user(name="An")
    make_book(user, title="Old Book", created_at=T0)
    make_book(user, title="New Book", created_at=T0 + timedelta(days=1))
    data = client.get("/api/v1/books").json()
    assert [b["title"] for b in data["items"]] == ["New Book", "Old Book"]
    assert data["total"] == 2


def test_item_shape_and_z_timestamp(client, make_user, make_book):
    user = make_user(name="An")
    make_book(user, title="The Little Prince", description="A pilot meets a boy.", created_at=T0)
    item = client.get("/api/v1/books").json()["items"][0]
    assert item["title"] == "The Little Prince"
    assert item["description"] == "A pilot meets a boy."
    assert item["uploader_id"] == user.id
    assert item["uploader_name"] == "An"
    assert item["chapter_count"] == 0
    assert item["created_at"] == "2026-10-01T09:00:00Z"


def test_chapter_count_excludes_deleted_chapters(client, make_user, make_book, make_chapter):
    book = make_book(make_user(), created_at=T0)
    make_chapter(book, number=1)
    make_chapter(book, number=2)
    make_chapter(book, number=3, deleted_at=datetime.now(timezone.utc))
    item = client.get("/api/v1/books").json()["items"][0]
    assert item["chapter_count"] == 2


def test_q_filters_case_insensitively(client, make_user, make_book):
    user = make_user()
    make_book(user, title="The Little Prince", created_at=T0)
    make_book(user, title="Dracula", created_at=T0)
    res = client.get("/api/v1/books", params={"q": "little"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "The Little Prince"


def test_deleted_books_are_hidden(client, make_user, make_book):
    user = make_user()
    make_book(user, title="Alive", created_at=T0)
    make_book(user, title="Dead", created_at=T0, deleted_at=datetime.now(timezone.utc))
    data = client.get("/api/v1/books").json()
    assert [b["title"] for b in data["items"]] == ["Alive"]
    assert data["total"] == 1


def test_pagination(client, make_user, make_book):
    user = make_user()
    for i in range(5):
        make_book(user, title=f"Book {i}", created_at=T0 + timedelta(hours=i))
    data = client.get("/api/v1/books", params={"page": 2, "size": 2}).json()
    assert data["page"] == 2
    assert data["size"] == 2
    assert data["total"] == 5
    # newest first: Book 4, Book 3 | Book 2, Book 1 | Book 0
    assert [b["title"] for b in data["items"]] == ["Book 2", "Book 1"]


def test_invalid_page_and_size_are_rejected(client):
    assert client.get("/api/v1/books", params={"page": 0}).status_code == 422
    assert client.get("/api/v1/books", params={"size": 0}).status_code == 422
    assert client.get("/api/v1/books", params={"size": 101}).status_code == 422


# --- Endpoint 4: GET /api/v1/books/{id} ---


def test_book_detail_shape(client, make_user, make_book, make_chapter):
    user = make_user(name="An")
    book = make_book(user, title="The Little Prince", description="A pilot meets a boy.", created_at=T0)
    make_chapter(book, number=1, title="Chapter I")
    make_chapter(book, number=2, title="Chapter II")
    res = client.get(f"/api/v1/books/{book.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == book.id
    assert data["title"] == "The Little Prince"
    assert data["description"] == "A pilot meets a boy."
    assert data["uploader_id"] == user.id
    assert data["uploader_name"] == "An"
    assert data["created_at"] == "2026-10-01T09:00:00Z"
    assert data["chapters"] == [
        {"number": 1, "title": "Chapter I"},
        {"number": 2, "title": "Chapter II"},
    ]


def test_book_detail_chapters_sorted_by_number(client, make_user, make_book, make_chapter):
    book = make_book(make_user())
    make_chapter(book, number=3, title="Chapter III")
    make_chapter(book, number=1, title="Chapter I")
    make_chapter(book, number=2, title="Chapter II")
    data = client.get(f"/api/v1/books/{book.id}").json()
    assert [c["number"] for c in data["chapters"]] == [1, 2, 3]


def test_book_detail_hides_deleted_chapters(client, make_user, make_book, make_chapter):
    book = make_book(make_user())
    make_chapter(book, number=1)
    make_chapter(book, number=2, deleted_at=datetime.now(timezone.utc))
    data = client.get(f"/api/v1/books/{book.id}").json()
    assert [c["number"] for c in data["chapters"]] == [1]


def test_book_detail_without_chapters(client, make_user, make_book):
    book = make_book(make_user())
    data = client.get(f"/api/v1/books/{book.id}").json()
    assert data["chapters"] == []


def test_book_detail_missing_book_is_404(client):
    res = client.get("/api/v1/books/999999")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "BOOK_NOT_FOUND"


def test_book_detail_deleted_book_is_404(client, make_user, make_book):
    book = make_book(make_user(), deleted_at=datetime.now(timezone.utc))
    res = client.get(f"/api/v1/books/{book.id}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "BOOK_NOT_FOUND"


def test_book_detail_non_integer_id_is_422(client):
    res = client.get("/api/v1/books/abc")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# --- Endpoint 5: GET /api/v1/books/{id}/chapters/{number} ---


def test_read_chapter(client, make_user, make_book, make_chapter):
    book = make_book(make_user(), title="The Little Prince")
    make_chapter(
        book,
        number=3,
        title="Chapter III",
        content="The stars are beautiful.",
    )
    res = client.get(f"/api/v1/books/{book.id}/chapters/3")
    assert res.status_code == 200
    assert res.json() == {
        "book_id": book.id,
        "number": 3,
        "title": "Chapter III",
        "content": "The stars are beautiful.",
    }


def test_read_chapter_missing_book_is_404(client):
    res = client.get("/api/v1/books/999999/chapters/1")
    assert res.status_code == 404
    assert res.json()["error"] == {
        "code": "BOOK_NOT_FOUND",
        "message": "Book 999999 does not exist",
    }


def test_read_chapter_deleted_book_is_404(client, make_user, make_book):
    book = make_book(make_user(), deleted_at=datetime.now(timezone.utc))
    res = client.get(f"/api/v1/books/{book.id}/chapters/1")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "BOOK_NOT_FOUND"


def test_read_missing_chapter_is_404(client, make_user, make_book):
    book = make_book(make_user())
    res = client.get(f"/api/v1/books/{book.id}/chapters/1")
    assert res.status_code == 404
    assert res.json()["error"] == {
        "code": "CHAPTER_NOT_FOUND",
        "message": f"Chapter 1 of book {book.id} does not exist",
    }


def test_read_deleted_chapter_is_404(client, make_user, make_book, make_chapter):
    book = make_book(make_user())
    make_chapter(book, number=1, deleted_at=datetime.now(timezone.utc))
    res = client.get(f"/api/v1/books/{book.id}/chapters/1")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "CHAPTER_NOT_FOUND"


def test_read_chapter_number_zero_is_422(client, make_user, make_book):
    book = make_book(make_user())
    res = client.get(f"/api/v1/books/{book.id}/chapters/0")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_read_non_integer_chapter_number_is_422(client, make_user, make_book):
    book = make_book(make_user())
    res = client.get(f"/api/v1/books/{book.id}/chapters/abc")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
