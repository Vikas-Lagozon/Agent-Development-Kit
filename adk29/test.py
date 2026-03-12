# count_characters.py

file_path = "data.txt"

try:
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
        char_count = len(content)

    print("File loaded successfully.")
    print(f"Total number of characters: {char_count}")

except FileNotFoundError:
    print("Error: data.txt file not found.")
except Exception as e:
    print(f"An error occurred: {e}")

