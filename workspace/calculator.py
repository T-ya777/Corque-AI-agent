"""
A simple Python calculator that performs basic arithmetic operations.
"""


def get_number(prompt: str) -> float:
    """
    Get a number from the user with input validation.
    
    Args:
        prompt: The prompt to display to the user
        
    Returns:
        The validated number entered by the user
    """
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Error: Please enter a valid number.")


def get_operation() -> str:
    """
    Get the operation choice from the user.
    
    Returns:
        A string representing the chosen operation
    """
    print("\nSelect operation:")
    print("1. Addition (+)")
    print("2. Subtraction (-)")
    print("3. Multiplication (*)")
    print("4. Division (/)")
    print("5. Exit")
    
    while True:
        choice = input("\nEnter choice (1-5): ").strip()
        if choice in ['1', '2', '3', '4', '5']:
            return choice
        print("Error: Please enter a number from 1 to 5.")


def perform_operation(num1: float, num2: float, operation: str) -> float | str:
    """
    Perform the specified arithmetic operation.
    
    Args:
        num1: The first number
        num2: The second number
        operation: The operation to perform ('+', '-', '*', '/')
        
    Returns:
        The result of the operation, or an error message for division by zero
    """
    match operation:
        case '1':
            return num1 + num2
        case '2':
            return num1 - num2
        case '3':
            return num1 * num2
        case '4':
            if num2 == 0:
                return "Error: Division by zero is not allowed."
            return num1 / num2
        case _:
            return "Error: Invalid operation."


def get_operation_symbol(operation: str) -> str:
    """Get the symbol for the given operation choice."""
    symbols = {'1': '+', '2': '-', '3': '*', '4': '/'}
    return symbols.get(operation, '?')


def main() -> None:
    """Main function to run the calculator."""
    print("=" * 40)
    print("       SIMPLE PYTHON CALCULATOR")
    print("=" * 40)
    
    while True:
        operation = get_operation()
        
        if operation == '5':
            print("\nThank you for using the calculator. Goodbye!")
            break
        
        num1 = get_number("\nEnter first number: ")
        num2 = get_number("Enter second number: ")
        
        symbol = get_operation_symbol(operation)
        result = perform_operation(num1, num2, operation)
        
        if isinstance(result, str):  # Error message
            print(f"\n{result}")
        else:
            print(f"\nResult: {num1} {symbol} {num2} = {result}")
        
        print("-" * 40)


if __name__ == "__main__":
    main()