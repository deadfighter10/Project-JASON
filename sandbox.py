def functionA(numberIn):
    result = numberIn * numberIn
    print("The result is:", result)

def functionB(num1, num2):
    num3 = num1 + num2
    result = functionC(num3)
    return result

def functionC(numberIn):
    result = numberIn * 2
    return result

def triple(number):
    return [number, number, number]

def sumOdds(num):
    for i in range(num):
        if i % 2 == 1:
            print(i, end=' ')