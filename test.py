import bittensor as bt

if __name__ == "__main__":
    confirm = input(f"Are you sure? (y/n)")
    if confirm.lower() != 'y':
        test_value = "Hello"
        
    print(test_value)