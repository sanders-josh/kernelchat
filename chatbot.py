import os
import sys
import re

from openai import OpenAI, APIStatusError

import configs

bot:OpenAI = None
chat_history:dict = None

def get_bot() -> OpenAI:
    """
    Get an instance of the chatbot if not already connected.
    """
    global bot
    if bot is not None:
        return bot

    bot = OpenAI(base_url="https://router.huggingface.co/v1",
                 api_key=os.environ["HF_TOKEN"])

    return bot

def prompt_bot(prompt:str, *,
               model:str='deepseek-ai/DeepSeek-V4-Pro',
               prompt_history:list[dict]=None):
    """
    Connect to bot if not connected.
    Submit prompt and return response stream with current message history.
    """
    bot = get_bot()

    prompt={"role": "user",
            "content": prompt}
    
    messages = ([prompt]
                if prompt_history is None
                else [*prompt_history, prompt])

    try:    
        return bot.chat.completions.create(model=model,
                                           messages=messages,
                                           stream=True), \
                messages
    except APIStatusError as e:
        print(e)
        return None, messages        

def monitor_stream(stream):
    """
    Display output stream from bot and return accumulated response.
    """
    response = ""
    for chunk in stream:
        if (not getattr(chunk, "choices", None)
            or len(chunk.choices) == 0):
            continue

        delta = chunk.choices[0].delta
        if delta and delta.content:
            response += delta.content
            print(delta.content, end="", flush=True)

    return {"role": "assistant", "content": response}

def user_is_done(text) -> bool:
    """
    Detect if the user is done with the chat.
    """
    GOODBYE_RE = re.compile(r"\b(bye|goodbye|see you|cya|later|"
                            + r"quit|exit|done|that's all|that is all|no thanks)\b", re.I)

    text = text.strip().lower()
    return text in ["q", "quit", "exit"] or bool(GOODBYE_RE.search(text))

def main():
    print()

    # get command line arguments for model, persona, etc.
    config = configs.from_args(sys.argv)

    # add persona to prompt history if requested
    history = []
    if (persona := config.get('persona')) is not None:
        history.append(persona)

    # get model if requested
    model = config.get('model')

    # prompt the bot to start the chat
    prompt = "Greet the user and introduce yourself."

    while True:
        # prompt bot; get stream to monitor and updated chat history
        stream, chat_history = prompt_bot(prompt,
                                          model=model,
                                          prompt_history=history)

        # exit on exceptions, goodbyes, etc.
        if stream is None:
            break
    
        # stream output to cli and update chat history when done 
        response = monitor_stream(stream)
        history.append(response)
        print()
        
        # exit if requested by user
        if user_is_done(prompt):
            break

        # get next prompt from user
        prompt = input('\n -> ')

    # endwhile
    print()

if __name__=='__main__':
    main()

