from llm_service import LocalLlamaService

if __name__ == "__main__":
    llm_service = LocalLlamaService()
    prompt = "Once upon a time in a land far, far away,"
    
    while True:
        prompt = input("Enter your prompt (or 'q' to quit): ")
        if prompt.lower() == 'q':
            break
        print("Generating response:\n")
        for chunk in llm_service. generate_text_stream(prompt):
            print(chunk, end='', flush=True)
        print("\nEnd of response.\n")