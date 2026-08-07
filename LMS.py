#Variable : for data storage 
#Print Statements : to print data on console 
# Loops : for repeatitive task 
# Arrays : for storing collection of data
# While Loop : executing program without defined ending point
# Conditional Statements : control the flow of program
#break Statements :  to break or stop the program any time we want

# this_is_a_variable = "Ahmed"
# names  = ["Ahmed" , "Musawir", "Ali" , "John"]

# for name in names:
#    print("-Name : ",name)

# for x in range(10):
#    print(x)


# print("THis is VAribale output : ", this_is_a_variable)
# print("THis is a array output : ",this_is_array[1])

print("------- Welcome To Library Management System -------------")

books = []
borrowerd_books = []

while True:
    print("\n-----------LMS Menu--------")
    print("1. Add Books")
    print("2. View Books")
    print("3. Borrow Books")
    print("4. Return books")
    print("5. Exit")
    
    choice = input("Enter Your Choice: ")
    
    if choice == '1':
        book_name = input("Enter Book Name : ")
        books.append(book_name)
        print("Book Added")
      #   0 1 2 3 4 5 67 8/
    elif choice == '2':
        if len(books) == 0:
            print("No books available")
        else:
            print("\nAvailable Books:")
            for book in books:
                print("-", book)
                
    elif choice == '3':
        if len(books) == 0:
            print("No books available to borrow")
        else:
            book_name = input("Enter Book Name to Borrow: ")
            
            found_book = next((b for b in books if b.lower() == book_name.lower()), None)
            
            if found_book:
                books.remove(found_book)
                borrowerd_books.append(found_book)
                print("Book Borrowed Successfully")
            else:
                print("Book Not Available")
                
    elif choice == '4':
        book_name = input("Enter Book to Return : ")
        
        found_borrowed = next((b for b in borrowerd_books if b.lower() == book_name.lower()), None)
       
        
        if found_borrowed:
            borrowerd_books.remove(found_borrowed)
            books.append(found_borrowed)
            print("Book Returned Successfully")
        else:
            print("This Book Was Not Found / or not borrowed")
            
    elif choice == '5':
        print("Exiting The program")
        break
        
    else:
        print("Invalid Choice Try Again")
