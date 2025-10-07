from chatbot_logic import get_destination_info, detect_language

def chatbot():
    print("Bot: Hello! How can I help you today?")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["bye", "exit", "quit"]:
            print("Bot: Goodbye! Safe travels!")
            break

        if len(user_input.split()) > 1 and detect_language(user_input) != "en":
            print("Bot: Sorry, I can only respond in English. Please type in English.")
            continue

        if user_input.lower() in ["hi", "hello", "hey"]:
            print("Bot: How can I help you? Please tell me a destination name.")
            continue

        city = user_input.title()
        bot_reply = get_destination_info(city)
        print(f"Bot: {bot_reply}")

if __name__ == "__main__":
    chatbot()
