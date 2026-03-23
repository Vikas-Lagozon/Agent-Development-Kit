# Instructions to Run the Fibonacci Sequence Generator

This document provides instructions on how to run the Python script `fibonacci.py` to generate a Fibonacci sequence.

## Prerequisites

Before running the script, ensure you have the following:

-   Python 3.6 or higher installed on your system.
-   A text editor or IDE to view and edit the files (optional).

## Setup

1.  **Create a project directory:**

    If you don't already have one, create a directory for the project.  For example, `fibonacci_generator`.

2.  **Place the files:**

    Ensure that the following files are present in the project directory:

    -   `fibonacci.py` (the Python script)
    -   `instructions.md` (this instruction file)
    -   `.env.example` (example environment variables - optional)
    -   `requirements.txt` (lists the dependencies - optional for this script since it has no dependencies)
    -   `setup.py` (sets up the project - optional for this script since it has no dependencies)

3. **(Optional) Create a virtual environment:**

    It's recommended to use a virtual environment to manage dependencies.  Navigate to the project directory in your terminal and run:

    ```bash
    python3 -m venv venv
    ```

    Activate the virtual environment:

    -   On Windows:

        ```bash
        venv\Scripts\activate
        ```

    -   On macOS and Linux:

        ```bash
        source venv/bin/activate
        ```

4.  **(Optional) Install dependencies:**

    If there's a `requirements.txt` file, install the dependencies using pip:

    ```bash
    pip install -r requirements.txt
    ```

## Running the Script

1.  **Open a terminal or command prompt:**

    Navigate to the project directory where `fibonacci.py` is located.

2.  **Execute the script:**

    Run the script using the Python interpreter:

    ```bash
    python fibonacci.py
    ```

3.  **Enter the number of terms:**

    The script will prompt you to enter the number of Fibonacci terms you want to generate.  Enter a non-negative integer and press Enter.

4.  **View the Fibonacci sequence:**

    The script will output the Fibonacci sequence up to the specified number of terms.

## Example

```
Enter the number of Fibonacci terms to generate: 10
Fibonacci sequence: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

## Error Handling

-   If you enter a non-integer value, the script will display an "Invalid input" error message.
-   If you enter a negative integer, the script will prompt you to enter a non-negative integer.
-   If any unexpected error occurs during script execution, a message describing the error will be displayed.
