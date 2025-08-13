from marshmallow import Schema, fields

class QuestionSchema(Schema):
    id = fields.Int(required=True)
    text = fields.Str(required=True)
    score = fields.Float(required=True)

class AnswerSchema(Schema):
    question_id = fields.Int(required=True)
    answer_text = fields.Str(required=True)
    user_id = fields.Str(required=True)
