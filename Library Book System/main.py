from fastapi import FastAPI, Query, status, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

# this is what user sends when they want to borrow a book
# basically we're validating everything here before it even hits our logic
class BorrowRequest(BaseModel):
    member_name: str = Field(..., min_length=2)  # at least 2 chars...
    book_id: int = Field(..., gt=0)  # book id must be > 0 obviously
    borrow_days: int = Field(..., gt=0)  # can't borrow for 0 days or forever, we'll handle logic manually now
    member_id: str = Field(..., min_length=4)  # some basic id check
    member_type: str = "regular"  # could be "regular" or "premium"

# model for adding new books
class NewBook(BaseModel):
    title: str = Field(..., min_length=2)
    author: str = Field(..., min_length=2)
    genre: str = Field(..., min_length=2)
    is_available: bool = True  # default true... new books should be available


# Sample data (in-memory database)
books = [
    {"id": 1, "title": "1984", "author": "George Orwell", "genre": "Fiction", "is_available": True},
    {"id": 2, "title": "A Brief History of Time", "author": "Stephen Hawking", "genre": "Science", "is_available": True},
    {"id": 3, "title": "Sapiens", "author": "Yuval Noah Harari", "genre": "History", "is_available": True},
    {"id": 4, "title": "Clean Code", "author": "Robert C. Martin", "genre": "Tech", "is_available": True},
    {"id": 5, "title": "The Alchemist", "author": "Paulo Coelho", "genre": "Fiction", "is_available": True},
    {"id": 6, "title": "The Selfish Gene", "author": "Richard Dawkins", "genre": "Science", "is_available": True},
]

@app.get("/")
def home():
    return {"message": "Welcome to City Public Library"}


@app.get("/books")
def get_books():
    total_count = len(books)
    available_count = sum(1 for book in books if book["is_available"])

    return {
        "total_books": total_count,
        "available_books": available_count,
        "books": books
    }

@app.get("/books/summary")
def get_books_summary():
    total_books = len(books)
    
    # counting available and borrowed
    available_count = sum(1 for book in books if book["is_available"])
    borrowed_count = total_books - available_count  # whatever is not available is borrowed
    
    # genre breakdown... building dict manually
    genre_count = {}
    
    for book in books:
        genre = book["genre"]
        
        # if genre not seen before, initialize it
        if genre not in genre_count:
            genre_count[genre] = 0
        
        # increment count
        genre_count[genre] += 1

    return {
        "total_books": total_books,
        "available_books": available_count,
        "borrowed_books": borrowed_count,
        "genre_breakdown": genre_count
    }


@app.get("/books/filter")
def filter_books(
    genre: str = Query(None),
    author: str = Query(None),
    is_available: bool = Query(None)
):
    # calling helper... keeps endpoint clean
    result = filter_books_logic(genre, author, is_available)

    return {
        "count": len(result),
        "books": result
    }

@app.get("/books/search")
def search_books(keyword: str):
    # making keyword lowercase once... easier to compare
    keyword = keyword.lower()

    results = []

    # loop through all books and check both title + author
    for book in books:
        if (
            keyword in book["title"].lower() or
            keyword in book["author"].lower()
        ):
            results.append(book)  # match found, add it

    return {
        "total_found": len(results),
        "books": results
    }

@app.get("/books/sort")
def sort_books(sort_by: str = "title", order: str = "asc"):
    # allowed values (keeping it strict)
    allowed_sort_fields = ["title", "author", "genre"]
    allowed_order = ["asc", "desc"]

    # validate sort_by
    if sort_by not in allowed_sort_fields:
        return {"error": f"Invalid sort_by. Allowed: {allowed_sort_fields}"}

    # validate order
    if order not in allowed_order:
        return {"error": f"Invalid order. Allowed: {allowed_order}"}

    # decide sorting direction
    reverse = True if order == "desc" else False

    # sorting logic
    # using lower() so sorting is case-insensitive
    sorted_books = sorted(
        books,
        key=lambda book: book[sort_by].lower(),
        reverse=reverse
    )

    return {
        "sort_by": sort_by,
        "order": order,
        "total_books": len(sorted_books),
        "books": sorted_books
    }

@app.get("/books/page")
def paginate_books(page: int = 1, limit: int = 3):
    # basic safety... not going too strict but avoiding nonsense inputs
    if page < 1 or limit < 1:
        return {"error": "page and limit must be greater than 0"}

    total = len(books)

    # calculate total pages (classic formula)
    total_pages = (total + limit - 1) // limit  # ceiling division...

    # calculate slice indexes
    start = (page - 1) * limit
    end = start + limit

    # slice the books list
    paginated_books = books[start:end]

    return {
        "total": total,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "books": paginated_books
    }

@app.get("/books/browse")
def browse_books(
    keyword: str = None,
    sort_by: str = "title",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):
    # step 1: start with all books
    result = books

    # ------------------ FILTER ------------------
    if keyword is not None:
        keyword_lower = keyword.lower()

        # filtering on title + author
        result = [
            book for book in result
            if keyword_lower in book["title"].lower()
            or keyword_lower in book["author"].lower()
        ]

    # ------------------ SORT ------------------
    allowed_sort_fields = ["title", "author", "genre"]
    allowed_order = ["asc", "desc"]

    if sort_by not in allowed_sort_fields:
        return {"error": f"Invalid sort_by. Allowed: {allowed_sort_fields}"}

    if order not in allowed_order:
        return {"error": f"Invalid order. Allowed: {allowed_order}"}

    reverse = True if order == "desc" else False

    result = sorted(
        result,
        key=lambda book: book[sort_by].lower(),
        reverse=reverse
    )

    # ------------------ PAGINATION ------------------
    if page < 1 or limit < 1:
        return {"error": "page and limit must be greater than 0"}

    total = len(result)
    total_pages = (total + limit - 1) // limit

    start = (page - 1) * limit
    end = start + limit

    paginated_result = result[start:end]

    # ------------------ FINAL RESPONSE ------------------
    return {
        "keyword": keyword,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit,
        "total_results": total,
        "total_pages": total_pages,
        "books": paginated_result
    }

@app.get("/books/{book_id}")
def get_book_by_id(book_id: int):
    # loop through all books...
    for book in books:
        if book["id"] == book_id:
            return book  # found it, return immediately
    
    # if we reach here, means no book matched
    return {"error": "Book not found"}


# this will store who borrowed what... empty for now obviously
borrow_records = []

# simple counter to give each borrow record a unique id
record_counter = 1

# queue for books that are currently unavailable
# like a waiting list... first come first serve
queue = []

# helper to find a book by id
def find_book(book_id: int):
    for book in books:
        if book["id"] == book_id:
            return book  # found it
    
    return None  # nothing found


# helper to calculate return date (super simplified logic)
# we're just pretending today is Day 15... don't overthink it 
def calculate_due_date(borrow_days: int, member_type: str):
    # okay so now rules change based on member type
    
    if member_type == "premium":
        max_days = 60  # premium gets more freedom 
    else:
        max_days = 30  # regular users... sorry, rules are rules

    # if user tries to exceed limit, block it
    if borrow_days > max_days:
        return f"Error: {member_type} members can borrow for max {max_days} days"

    # otherwise calculate normally
    return f"Return by: Day {15 + borrow_days}"


# helper to filter books based on optional params
# using "is not None" so we only filter when user actually sends something
def filter_books_logic(genre=None, author=None, is_available=None):
    filtered = books  # start with all books

    # filter by genre if provided
    if genre is not None:
        filtered = [book for book in filtered if book["genre"].lower() == genre.lower()]

    # filter by author if provided
    if author is not None:
        filtered = [book for book in filtered if author.lower() in book["author"].lower()]

    # filter by availability if provided
    if is_available is not None:
        filtered = [book for book in filtered if book["is_available"] == is_available]

    return filtered


@app.post("/borrow")
def borrow_book(request: BorrowRequest):
    global record_counter  # we need this to increment IDs

    # step 1: check if book exists
    book = find_book(request.book_id)
    if not book:
        return {"error": "Book not found"}  # simple error

    # step 2: check if already borrowed
    if not book["is_available"]:
        return {"error": "Book is already borrowed"}  # can't borrow twice obviously

    # step 3: mark book as borrowed
    book["is_available"] = False

    # step 4: calculate due date
    due_date = calculate_due_date(request.borrow_days, request.member_type)

    # step 5: create borrow record
    record = {
        "record_id": record_counter,
        "member_name": request.member_name,
        "member_id": request.member_id,
        "book_id": request.book_id,
        "borrow_days": request.borrow_days,
        "due_date": due_date
    }

    # step 6: save record
    borrow_records.append(record)

    # increment counter for next record
    record_counter += 1

    # return confirmation
    return {
        "message": "Book borrowed successfully",
        "record": record
    }


@app.get("/borrow-records")
def get_borrow_records():
    # just returning everything we have + total count
    return {
        "total_records": len(borrow_records),
        "records": borrow_records
    }

@app.get("/borrow-records/search")
def search_borrow_records(member_name: str):
    # case-insensitive search... same idea as books
    keyword = member_name.lower()

    results = []

    for record in borrow_records:
        if keyword in record["member_name"].lower():
            results.append(record)

    return {
        "total_found": len(results),
        "records": results
    }

@app.get("/borrow-records/page")
def paginate_borrow_records(page: int = 1, limit: int = 3):
    # basic validation
    if page < 1 or limit < 1:
        return {"error": "page and limit must be greater than 0"}

    total = len(borrow_records)

    # same pagination formula again
    total_pages = (total + limit - 1) // limit

    start = (page - 1) * limit
    end = start + limit

    paginated_records = borrow_records[start:end]

    return {
        "total": total,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "records": paginated_records
    }


@app.post("/books", status_code=status.HTTP_201_CREATED)
def add_book(book: NewBook):
    # check duplicate title (case-insensitive)
    for existing_book in books:
        if existing_book["title"].lower() == book.title.lower():
            return {"error": "Book with this title already exists"}  # yeah simple rejection

    # generate new id (max id + 1...)
    new_id = max(book["id"] for book in books) + 1 if books else 1

    # create new book object
    new_book = {
        "id": new_id,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "is_available": book.is_available
    }

    # add to our fake DB
    books.append(new_book)

    return new_book  # FastAPI will return with 201 automatically



@app.put("/books/{book_id}")
def update_book(
    book_id: int,
    genre: str = Query(None),
    is_available: bool = Query(None)
):
    # find the book first
    book = find_book(book_id)

    # if not found → proper 404 (not just returning dict)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # apply updates only if values are provided
    # using "is not None" is key here
    if genre is not None:
        book["genre"] = genre  # updating genre

    if is_available is not None:
        book["is_available"] = is_available  # updating availability

    # return updated book
    return book

@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    # find the book first
    book = find_book(book_id)

    # if not found → proper error
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # remove from list
    books.remove(book)  # this directly mutates the list

    # return confirmation
    return {
        "message": f"Book '{book['title']}' deleted successfully"
    }

@app.post("/queue/add")
def add_to_queue(member_name: str, book_id: int):
    # step 1: check if book exists
    book = find_book(book_id)
    if not book:
        return {"error": "Book not found"}

    # step 2: only allow queue if book is NOT available
    if book["is_available"]:
        return {"error": "Book is available, no need to join queue"}

    # step 3: add to queue
    entry = {
        "member_name": member_name,
        "book_id": book_id
    }

    queue.append(entry)

    return {
        "message": "Added to queue",
        "entry": entry
    }

@app.post("/return/{book_id}")
def return_book(book_id: int):
    global record_counter  # needed for new borrow record

    # step 1: find the book
    book = find_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # step 2: mark as available first
    book["is_available"] = True

    # step 3: check if anyone is waiting in queue for this book
    for entry in queue:
        if entry["book_id"] == book_id:
            # found first person waiting (queue is FIFO by default list order)

            # remove them from queue
            queue.remove(entry)

            # mark book as borrowed again
            book["is_available"] = False

            # create new borrow record automatically
            due_date = calculate_due_date(15, "regular")  
            # giving default 15 days + regular... keeping it simple

            record = {
                "record_id": record_counter,
                "member_name": entry["member_name"],
                "member_id": "AUTO",  # we don't have it in queue, so placeholder
                "book_id": book_id,
                "borrow_days": 7,
                "due_date": due_date
            }

            borrow_records.append(record)
            record_counter += 1

            return {
                "message": "Book returned and re-assigned to next member in queue",
                "new_borrow_record": record
            }

    # step 4: no one waiting -> book stays available
    return {
        "message": "Book returned and is now available"
    }