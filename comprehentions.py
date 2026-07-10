numbers=[x for x in range (3,350,2) if x%3 ==0 ]
print (numbers)
dictionary ={key:value for key,value in enumerate(numbers)}
tuple=tuple(x for x in range (2,543,12) if x<324)
print ("dictionary:",dictionary)
print ("tuple",tuple)
db_result = {
    "users": {
        101: {
            "name": "Ana",
            "age": 25,
            "orders": [
                {"id": 5001, "product": "Laptop", "price": 1200},
                {"id": 5002, "product": "Mouse", "price": 25}
            ]
        },
        102: {
            "name": "Luis",
            "age": 30,
            "orders": [
                {"id": 5003, "product": "Teclado", "price": 45}
            ]
        },
        103: {
            "name": "María",
            "age": 28,
            "orders": []
        }
    },
    "courses": {
        "python": {"students": [101, 103], "duration": "3 months"},
        "docker": {"students": [102], "duration": "2 months"}
    }
}
