from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired
from wtforms.widgets import TextArea

# Form for selecting a prompt
# class PromptForm(FlaskForm):
#     title = SelectField("Prompt", validators=[DataRequired()], choices=str)
#     submit = SubmitField("Start")

# Form for entering a reply
class ReplyForm(FlaskForm):
    conv_id = HiddenField()
    reply = StringField("Reply", widget=TextArea(), validators=[DataRequired()])
    submit = SubmitField("Submit")

class ChatForm(FlaskForm):
    text = StringField("Your response:")
    submit = SubmitField("Submit")

class UpdatePromptForm(FlaskForm):
    _id = HiddenField("_id")
    title = StringField("Title:")
    prompt = StringField("Prompt:", widget=TextArea())
    instruction = StringField("Instruction: ")
    submit = SubmitField("Update")

class DeletePromptForm(FlaskForm):
    _id = HiddenField("_id")
    submit = SubmitField("Delete")

class NewPromptForm(FlaskForm):
    title = StringField("Title:")
    prompt = StringField("Prompt:", widget=TextArea())
    instruction = StringField("Instruction: ")
    submit = SubmitField("Add")