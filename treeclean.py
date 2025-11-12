import os

EXCLUDE = {"venv", "__pycache__", ".git", "node_modules", "build", "dist", "migrations"}

def print_tree(root=".", prefix=""):
    items = sorted(os.listdir(root))
    for i, item in enumerate(items):
        if item in EXCLUDE:
            continue
        path = os.path.join(root, item)
        connector = "└── " if i == len(items) - 1 else "├── "
        print(prefix + connector + item)
        if os.path.isdir(path):
            new_prefix = prefix + ("    " if i == len(items) - 1 else "│   ")
            print_tree(path, new_prefix)

if __name__ == "__main__":
    print_tree(".")
