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
