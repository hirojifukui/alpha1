from flask import render_template, redirect, url_for, request
from .forms import ReplyForm, NewPromptForm, UpdatePromptForm, DeletePromptForm
from . import app
import pymongo
import time
from bson.objectid import ObjectId
import openai
#openai.api_key = "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"

# Default settings
native = "Japanese"
name = "Hiroji: "
user_id = "0000000001"
ai = "AI teacher: "
#grammer_check="この英語を文法的に必要なら標準的な英語に変更し、修正がある場合は、修正した点を日本語で文法的に説明してください。: "
#grammer_check="Correct this to standard English and explain the improvement pointd in " + native + ": "

# Connect to MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["prompts_db"]
prompts_collection = db["prompts"]
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



# Route for displaying the list of prompts
@app.route("/prompt/<_id>", methods=["GET"])
def prompt(_id):
    _id = logs_collection.insert_one({"time": time.ctime(), "user_id": user_id, "name": name, "prompt": ObjectId(_id) })
    print("prompt/inserted_id: ", str(_id.inserted_id))
    return redirect("/conversation/"+str(_id.inserted_id))

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
    if form.validate_on_submit():
        #prompt = prompts_collection.find_one({"title": title})["prompt"]
        # Check grammer of user reply
        print("Form.reply.data: ",form.reply.data)

        if form.reply.data.strip() != "Stop" and form.reply.data != "":
            print(form.conv_id.data)
            conv = logs_collection.find_one({"_id": ObjectId(_id)})["conv"]
            conv.append([name,form.reply.data])
            # logs_collection.update_one({"_id": ObjectId(_id)}, { "$set": {"conv": conv}})
            # prompt =grammer_check + str(form.reply.data)
            # print("Grammer Check Prompt: ", prompt)
            # aireply = ai_reply(prompt, 0.3)
            # # aireply = form.reply.data
            # print("Grammer Check Reply: ", aireply)
            # #conv.append([ai, aireply])
            # answer = aireply[:aireply.find(".")]
            # if answer[0] == "No changes needed." or answer[0] == form.reply.data:
            #     reply = form.reply.data
            # else:
            #     reply = answer[0]
            # print(conv)
            # prompt = f"{conv[-2][0]}{conv[-2][1]}\n{conv[-1][0]}{conv[-1][1]}\n{name}{form.reply.data}"
            prompt = f"{conv[-1][0]}{conv[-1][1]}\n{name}{form.reply.data}"
            print("Reply prompt: ", prompt)
            aireply = ai_reply(prompt, 0.5)
            # aireply = "After Grammer check"
            print("AI Reply: ", aireply)
            conv.append([ai,aireply])
            # Log the conversation in a log collection in MongoDB
            logs_collection.update_one({"_id": ObjectId(_id)}, { "$set": {"conv": conv}})
            print(conv)
            form.reply.data = ""
            return render_template("conversation.html", form=form, conv=conv)
        elif form.reply.data.strip() == "Stop":
            return redirect(url_for("index"))
        elif form.reply.data == "":
            form.reply.data = "Please enter your reply"
            return render_template("conversation.html", form=form, conv=conv)
        else:
            form.reply.data = ""
            return render_template("conversation.html", form=form, conv=conv)
    # Get the prompt from the MongoDB database based on the selected title 
    prompt_id = logs_collection.find_one({"_id": ObjectId(_id)})["prompt"]       
    prompt = prompts_collection.find_one({"_id": prompt_id})["prompt"]
    instruction = prompts_collection.find_one({"_id": prompt_id})["instruction"]
    print("Conversation prompt: ", prompt, instruction)
    # Send the prompt to GPT-3 API and get the reply
    conv = []
    aireply = ai_reply(prompt, 0.3)
    # aireply = "Temporally out of order."
    print("GET Reply: ", aireply)
    conv.append([ai,aireply])
    form = ReplyForm(conv_id = _id)
    logs_collection.update_one({"_id": ObjectId(_id)}, { "$set": {"conv": conv}})
    form.reply.data = ""
    return render_template("conversation.html", form=form, conv=conv, instruction = instruction)

# Route for adding a new prompt
@app.route("/new", methods=["GET", "POST"])
def new_prompt():
    form = NewPromptForm()
    if form.validate_on_submit():
        # Insert the new prompt into the prompts collection in MongoDB
        prompts_collection.insert_one({"title": form.title.data, "prompt": form.prompt.data, "instruction":form.instruction.data, "time_created": time.ctime()})
        return redirect(url_for("index"))
    return render_template("new_prompt.html", form=form)

@app.route("/update/<_id>", methods=["GET", "POST"])
def update_prompt(_id):
    form = UpdatePromptForm()
    if form.validate_on_submit():
        # Update the prompt in the prompts collection in MongoDB
        objInstance = ObjectId(form._id.data)
        prompts_collection.update_one({"_id": objInstance}, {"$set": {"title": form.title.data, "prompt": form.prompt.data, "instruction":form.instruction.data, "time_updated": time.ctime()}})
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