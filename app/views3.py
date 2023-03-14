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
@app.route("/conversation/<_id>", methods=["GET"])
def conversation(_id):
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
    td = {"key":key, "chat":chat_transcript, "msg_len":msg_len, "inst": prompt["instruction"]}
    return render_template("conversation.html", td = td, request="POST")

@app.route("/talk", methods=["GET", "POST"])
def talk():
    form = ReplyForm()
    if request.method == "POST":
        #prompt = prompts_collection.find_one({"title": title})["prompt"]
        # Check grammer of user reply
        # print("Form.reply.data: ",form.reply.data)
        print("Return key : ",request.form["key"])
        f = request.files['audio_data']
        # fk = request.form["key"]
        # print(fk)
        with open('audio.wav', 'wb') as audio:
            f.save(audio)
        print("Save audio.wav")
        audio_file = open('audio.wav', "rb")
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        print("Transript: ", transcript["text"])

        if transcript["text"].lower != "stop":
            instruction = request.form["inst"]
            key = request.form["key"]
            print("Key: ", key)
            prev_messages = logs_collection.find_one({"key": key})
            messages = prev_messages["messages"]
            messages.append({"role": "user", "content": transcript["text"]})
            # message = {"role":"user", "content":form.reply.data}
            # messages.append(message)
            print("messages: ", messages)
            # ChatGPT
            response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
            # system_message = response["choices"][0]["message"]
            system_message = {"role": response["choices"][0]["message"]["role"], 
                              "content": response["choices"][0]["message"]["content"]}
            messages.append(system_message)
            print("Messages with AI reply: ", messages)
            # Text to Speech
            engine = pyttsx3.init()
            engine.say(system_message['content'])
            engine.runAndWait()
            engine.stop()

            logs_collection.update_one({"key": key}, { "$set": {"messages": messages}})
            print(messages)
            print("Msg_len: ", request.form["msg_len"], " type: ", type(request.form["msg_len"]))
            chat_transcript = messages[int(request.form["msg_len"]):]
            
            # form = ReplyForm(reply = "")
            # form.process()
            # form.reply.data = ""
            td = {"key":key, "chat":chat_transcript, "msg_len":request.form["msg_len"], "inst": request.form["inst"]}
            print("TD: ", td)
            return td
        # elif transcript["text"].lower == "stop":
        else:
            return redirect(url_for("index"))
        # elif transcript["text"].lower == "":
        #     form.reply.data = "Please enter your reply"
        #     return render_template("conversation.html", form=form, conv=chat_transcript, instruction = instruction)
        # else:
        #     form.reply.data = ""
        #     return render_template("conversation.html", form=form, conv=chat_transcript, instruction = instruction)
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
    td = {"key":key, "chat":chat_transcript, "msg_len":msg_len, "inst": prompt["instruction"]}
    return render_template("conversation.html", td=td, request = "POST")

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
        prompts_collection.insert_one({"pid": pid, "title": form.title.data,
             "description": form.description.data,"prompt": form.prompt.data,
             "time_created": datetime.now(), "instruction": form.instruction.data,
            "active":True})
        return redirect(url_for("index"))
    return render_template("new_prompt.html", form=form)

@app.route("/update/<_id>", methods=["GET", "POST"])
def update_prompt(_id):
    form = UpdatePromptForm()
    if form.validate_on_submit():
        # Update the prompt in the prompts collection in MongoDB
        prompts_collection.update_one({"_id": ObjectId(form._id.data)}, 
                                      {"$set": {"title": form.title.data, "description": form.description.data, 
                                        "prompt": form.prompt.data, "time_updated": datetime.now(),
                                        "instruction": form.instruction.data}})
        return redirect(url_for("index"))
    prompt = prompts_collection.find_one({"_id": ObjectId(_id)})
    form.title.data = prompt["title"]
    form.prompt.data = prompt["prompt"]
    form.instruction.data = prompt["instruction"]
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