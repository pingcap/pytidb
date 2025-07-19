from memory import init_clients, Memory, chat_with_memories

# Initialize clients
openai_client, tidb_client, embedding_fn = init_clients()

# Initialize memory
memory = Memory(tidb_client, embedding_fn, openai_client)


def main():
    print("Chat with AI (type 'exit' to quit)")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        print(f"AI: {chat_with_memories(user_input, memory, openai_client)}")


if __name__ == "__main__":
    main()
