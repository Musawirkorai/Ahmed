# Variable And datatype
name = "Ali 20 " #str
age = 20     #int
gpa = 3.75   #float
is_student = True #boolean

# Type Casting 
print(name , type(name))
print(age, type(age))
print(gpa , type(gpa))
print(is_student , type(is_student))



age_text = str(age)

age_int = int(age_text)

new_age = age + 30

print("new age : ",new_age)
print(type(new_age))
print("Age as text : ", age_text, type(age_text))


# Arthematic Opperators 
x= 10 
y =3 
print(x+y)
print(x-y)
print(x*y)
print(x/y)
print(x//y) #floor division
print(x%y) #reminder
print(x**y) #power

print(((x+y)/y)+2)

#Simple Calculator

num1 = int(input("Enter First Number : "))
num2 = int(input("Enter the Second Number : "))

print("-----------Calculator-----------")
print(f"{num1} + {num2} = {num1+num2}")
print(f"{num1} - {num2}  = {num1-num2}")
print(f"{num1} * {num2}  = {num1*num2}")
print(f"{num1} / {num2}  = {num1/num2}")