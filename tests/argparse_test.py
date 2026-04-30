import argparse

parser = argparse.ArgumentParser(description="my first argparser")
parser.add_argument("--name", required=True, help="Your name")
parser.add_argument("--age", type=int, help="your age")
parser.add_argument("--shout", action="store_true", help="shout the name")

args = parser.parse_args()

greeting = f"Hello, {args.name}! You are {args.age} years old!"
if args.shout:
    greeting = greeting.upper()

print(greeting)