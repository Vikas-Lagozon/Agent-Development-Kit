def fibonacci_sequence(n: int) -> list[int]:
    """
    Generates a Fibonacci sequence up to n terms.

    Args:
        n: The number of terms to generate.

    Returns:
        A list containing the Fibonacci sequence.
        Returns an empty list if n is zero or negative.
    """
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    else:
        list_fib = [0, 1]
        while len(list_fib) < n:
            next_fib = list_fib[-1] + list_fib[-2]
            list_fib.append(next_fib)
        return list_fib


if __name__ == "__main__":
    try:
        num_terms_str = input("Enter the number of Fibonacci terms to generate: ")
        num_terms = int(num_terms_str)

        if num_terms < 0:
            print("Please enter a non-negative integer.")
        else:
            fib_sequence = fibonacci_sequence(num_terms)
            print("Fibonacci sequence:", fib_sequence)

    except ValueError:
        print("Invalid input. Please enter a valid integer.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")