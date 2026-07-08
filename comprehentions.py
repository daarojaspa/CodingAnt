numbers=[x for x in range (3,350,2) if x%3 ==0 ]
print (numbers)
dictionary ={key:value for key,value in enumerate(numbers)}
tuple=(x for x in range (2,543,12) if x<324)
print ("dictionary:",dictionary)
print ("tuple",tuple)
