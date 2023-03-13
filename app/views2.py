from flask import render_template, redirect, url_for, request
from .forms import ReplyForm, NewPromptForm, UpdatePromptForm, DeletePromptForm
from . import app
import pymongo
from datetime import datetime
from bson.objectid import ObjectId
import openai
import pyttsx3
#openai.api_key = "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"

# Default settings
native = "Japanese"
name = "Hiroji: "
user_id = "0000000001"
ai = "assistant: "
#grammer_check="この英語を文法的に必要なら標準的な英語に変更し、修正がある場合は、修正した点を日本語で文法的に説明してください。: "
grammer_check="Correct this to standard English and explain the improvement pointd in " + native + ": "

# Connect to MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["prompts_db"]
prompts_collection = db["a2_prompts"]
logs_collection = db["conv_log"]
user_col = db["user"]

def transcribe(audio):
    global messages

    audio_file = open(audio, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)

    messages.append({"role": "user", "content": transcript["text"]})

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)

    system_message = response["choices"][0]["message"]
    messages.append(system_message)
    engine = pyttsx3.init()
    #subprocess.run(["say", system_message['content']])
    #subprocess.Popen([r"start", r"I:\My Drive\RISU\System development\OpenAI\Subprocess\tts_test.py"], shell=True)
    engine.say(system_message['content'])
    engine.runAndWait()
    engine.stop()
    chat_transcript = ""
    for message in messages:
        if message['role'] != 'system':
            chat_transcript += message['role'] + ": " + message['content'] + "\n\n"

    return chat_transcript


# Return GPT-3 response. Prompt and Temperature are inputs
def ai_reply(prompt, temp):
    return openai.Completion.create(
                engine="text-davinci-002",
                prompt=prompt,
                max_tokens=1024,
                n=1,
                stop=None,
                temperature=temp,
            )["choices"][0]["text"].strip()



@app.route("/", methods=["GET"])
def index():
    prompts = prompts_collection.find()
    prompt_list = [(str(prompt["_id"]), prompt["title"]) for prompt in prompts]
    return render_template("index.html", prompts = prompt_list)

# Route for handling the conversation
@app.route("/conversation/<_id>", methods=["GET", "POST"])
def conversation(_id):
    print("Conversation/inserted_id", _id)
    form = ReplyForm()
    if request.method == "POST" and form.validate_on_submit():
        #prompt = prompts_collection.find_one({"title": title})["prompt"]
        # Check grammer of user reply
        print("Form.reply.data: ",form.reply.data)
        print("Return key : ",form.key.data)
        if form.reply.data.strip() != "Stop" and form.reply.data != "":
            instruction = form.instruction.data
            key = form.key.data
            print("Key: ", key)
            prev_messages = logs_collection.find_one({"key": key})
            messages = prev_messages["messages"]
            message = {"role":"user", "content":form.reply.data}
            messages.append(message)
            print("messages: ", messages)
            # ChatGPT
            response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
            system_message = response["choices"][0]["message"]
            messages.append(system_message)

            # Text to Speech
            engine = pyttsx3.init()
            engine.say(system_message['content'])
            engine.runAndWait()
            engine.stop()

            logs_collection.update_one({"key": key}, { "$set": {"messages": messages}})
            print(messages)
            print("Msg_len: ", form.msg_len.data, " type: ", type(form.msg_len.data))
            chat_transcript = messages[int(form.msg_len.data):]
            # form = ReplyForm(reply = "")
            # form.process()
            form = ReplyForm(reply = "", key=key, msg_len = form.msg_len.data, instruction = instruction)
            return render_template("conversation.html", form=form, conv=chat_transcript, instruction = instruction)
        elif form.reply.data.strip() == "Stop":
            return redirect(url_for("index"))
        elif form.reply.data == "":
            form.reply.data = "Please enter your reply"
            return render_template("conversation.html", form=form, conv=chat_transcript, instruction = instruction)
        else:
            form.reply.data = ""
            return render_template("conversation.html", form=form, conv=chat_transcript, instruction = instruction)
    # Get the prompt from the MongoDB database based on the selected title 
    #prompt_id = logs_collection.find_one({"_id": ObjectId(_id)})["prompt"]       
    prompt = prompts_collection.find_one({"_id": ObjectId(_id)})
    print(prompt)
    messages = prompt["prompt"]
    msg_len = len(messages)
    print(datetime.now())
    key = str(datetime.now())+"+"+str(_id)
    print("key: ", key)
    _id = logs_collection.insert_one({"key": key, "user_id": user_id, "name": name, "msg_len": msg_len,
                                      "prompt": ObjectId(_id), "messages":messages})
    print("Conversation prompt: ", prompt)
    chat_transcript = []
    form = ReplyForm(request.values, key=key, conv=chat_transcript, msg_len = msg_len, instruction = prompt["instruction"])
    return render_template("conversation.html", form=form, instruction = prompt["instruction"])

# Route for adding a new prompt
@app.route("/new", methods=["GET", "POST"])
def new_prompt():
    form = NewPromptForm()
    if form.validate_on_submit():
        pid = 0
        for x in prompts_collection.find()["pid"]:
            if int(x) > pid:
                pid = x
        pid += 1
        # Insert the new prompt into the prompts collection in MongoDB
        prompts_collection.insert_one({"pid": pid,
            "title": form.title.data, "description": form.description.data,
            "prompt": form.prompt.data, "time_created": datetime.now(),
            "active":True})
        return redirect(url_for("index"))
    return render_template("new_prompt.html", form=form)

@app.route("/update/<_id>", methods=["GET", "POST"])
def update_prompt(_id):
    form = UpdatePromptForm()
    if form.validate_on_submit():
        # Update the prompt in the prompts collection in MongoDB
        objInstance = ObjectId(form._id.data)
        prompts_collection.update_one({"_id": objInstance}, 
                                      {"$set": {"title": form.title.data, "description": form.description.data, 
                                        "prompt": form.prompt.data, "time_updated": datetime.now()}})
        return redirect(url_for("index"))
    objInstance = ObjectId(_id)
    prompt = prompts_collection.find_one({"_id": objInstance})
    form.title.data = prompt["title"]
    form.prompt.data = prompt["prompt"]
    form._id.data = _id
    return render_template("update_prompt.html", form=form)

@app.route("/delete/<_id>", methods=["GET", "POST"])
def delete_prompt(title):
    prompt = prompts_collection.find_one({"title": title})
    if request.method == "POST":
        # Change the status of the record to "deactivated" in the prompts_collection in MongoDB
        prompts_collection.update_one({"title": title}, {"$set": {"status": "deactivated"}})
        return redirect(url_for("index"))
    return render_template("delete_prompt.html", prompt=prompt)