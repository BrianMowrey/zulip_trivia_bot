import html
import json
import requests
import random
import re
import time
from typing import Optional, Any, Dict, Tuple

class NotAvailableException(Exception):
    pass

class InvalidAnswerException(Exception):
    pass

class OpenTDB(object):
    def __init__(self, question_type = None):
       print("OpenTDB init")
       self.session_token = self.get_session_token()
       self.categories = self.get_categories()
       self.question_type = question_type
       self.message_ids = {}

    def get_session_token(self):
       # I'm not sure why but opentdb.com isn't verifying
       res = requests.get('https://opentdb.com/api_token.php?command=request', verify=False)
       data = res.json()
       #TODO: error handling for these requests...
       print("res=", data)
       if(data.get('response_code') == 0):
           return data.get('token')
       
    def get_categories(self):
        res = requests.get('https://opentdb.com/api_category.php', verify=False)
        data = res.json()
        print("[cat] data=", data)
        return data.get('trivia_categories')

class TriviaGame:
    def __init__(self, opentdb=None, phase='start'):
        """
        inits a new game
        """
        self.type = 'typed_then_multi'
        self.category_selection = 'vote'
        self.running = True
        self.phase = phase
        self.difficulty = 'medium'
        # store message_ids so we know what the reaction is for
        self.message_id = {}
        if opentdb:
            self.tdb = opentdb
        else:
             self.tdb = OpenTDB(question_type = 'multiple')

    def start(self):
        self.phase = start

    def voting_categories(self, num=5):
        """
        returns num categories from list
        also sets internal list so we can select from list
        once they vote
        """
        print("getting sampling from : ", self.tdb.categories)
        self.voting_categories = random.sample(self.tdb.categories, num)
        self.phase = 'category_vote'
        return self.voting_categories

    def set_message_id(self, key, message_id):
       """
       sets message id for certain messages
       """
       # I do this reverse for lookup
       self.message_id[message_id] = key

    def to_json(self):
        # TODO write this to dump object to storage
        """
            dumps game to json (for bot_storage)
        """
        return json.dumps({
            'type': self.type,
            'category_selection': self.category_selection,
            'phase': self.phase,
            'difficulty': self.difficulty,
            
        })        
    
    @classmethod
    def from_message(cls, message, opentdb=None):
        return cls(opentdb=opentdb)

    @classmethod
    def from_dict(cls, from_dict):
        """
        generates game from dict (from json)
        """
        return cls(phase=from_dict.get('phase'))

class TriviaGameHandler:
    def initialize(self, bot_handler):
        print('TriviaGame initialize')
        self.bot_handler = bot_handler
        self.tdb = OpenTDB(question_type='multiple')
        self.bot_handler._client.call_on_each_event(self.handle_event) 
        #self.client = self.bot_handler._client
        #initialize here so I'm just doing categories/token once
        self.game = None
        
    def usage(self) -> str:
        return '''
            This plugin will give users a trivia question from
            the open trivia database at opentdb.com.'''

    def handle_event(self, event: Dict[str, Any]) -> None:
        print("[event] event: ", event)
        if event.get('type') == 'message':
             message = event.get('message');
             print("subject: ", message.get('subject'))
             if message.get('subject') == 'game':
                 query = message['content']
                 print("found game message: ", message['content'])
                 if query == 'start game':
                     self.game = self.start_new_game(message)
                     return

        # reaction event:
        # [event] event:  {'op': 'add', 'message_id': 1230144, 'emoji_name': 'one', 'id': 2, 'reaction_type': 'unicode_emoji', 'emoji_code': '0031-20e3', 'type': 'reaction', 'user': {'user_id': 9, 'full_name': 'Brian Mowrey', 'email': 'brian@protectchildren.ca'}}        

    def handle_message(self, message: Dict[str, Any]) -> None:
        # don't do anything here since it's all handled in events
        return
        print("message=", message)
        query = message['content']
        print("query=",query)
        if query == 'start game':
                start_new_game(message)
                return
        elif query == 'stop game':
                stop_game(message)
        else:
           # anything else is a answer to a question
           pass

    def start_new_game(self, message: Dict[str, Any]) -> None:
        bot_response = "Starting Game..."
        # TODO: bail if currently running game
        game = TriviaGame.from_message(message=message, opentdb=self.tdb)
        print("starting game: ", game);
        self.bot_handler.storage.put("current_game", game.to_json()) 
        self.bot_handler.send_reply(message, bot_response)
        voting_categories = game.voting_categories()
        print("voting categories: ", voting_categories)
        response = "**Vote on Category**\n"
        for index, cat in enumerate(voting_categories):
            response += str(index + 1) + ". " + cat.get('name') + "\n"
        
        res = self.bot_handler.send_reply(message, response)
        print("reply res: ", res)
        if res.get('result') == 'success':
            print("SUCCESS")
            message_id = res.get('id')
            game.set_message_id('voting_categories', message_id)
            print("message_id=", message_id)
            time.sleep(0.5)
            for reaction in list([('one', '0031-20e3'), ('two', '0032-20e3'), ('three', '0033-20e3'), ('four', '0034-20e3'), ('five', '0035-20e3')]):
                print("adding reaction: ", reaction)
                time.sleep(0.5)                
                reaction_res = self.bot_handler._client.add_reaction({
                    'message_id': message_id, 
                    'emoji_name': reaction[0],
                    'emoji_code': reaction[1],  # this isn't needed in newer zulips...
                    'reaction_type': 'unicode_emoji',
                })
                print("reaction_res: ", reaction_res)
        return game
        
def stop_game(message: Dict[str, Any], bot_handler: Any) -> None:
    if bot_handler.storage.contains("current_game"):
        game = json.loads(bot_handler.storage.get("current_game"))
        print("game=", game)
        if game.get('running') is True:
 
            bot_response = "Stopping Game..."
            # TODO print stats
            bot_handler.storage.put("current_game", json.dumps({}))
            bot_handler.send_reply(message, bot_response)
            return
    bot_handler.send_reply(message, "game not running...")
   
def parse_answer(query: str) -> Tuple[str, str]:
    m = re.match(r'answer\s+(Q...)\s+(.)', query)
    if not m:
        raise InvalidAnswerException()

    quiz_id = m.group(1)
    answer = m.group(2).upper()
    if answer not in 'ABCD':
        raise InvalidAnswerException()

    return (quiz_id, answer)

def get_trivia_quiz() -> Dict[str, Any]:
    payload = get_trivia_payload()
    quiz = get_quiz_from_payload(payload)
    return quiz

def get_trivia_payload() -> Dict[str, Any]:

    url = 'https://opentdb.com/api.php?amount=1&type=multiple'

    try:
        data = requests.get(url)

    except requests.exceptions.RequestException:
        raise NotAvailableException()

    if data.status_code != 200:
        raise NotAvailableException()

    payload = data.json()
    return payload

def fix_quotes(s: str) -> Optional[str]:
    # opentdb is nice enough to escape HTML for us, but
    # we are sending this to code that does that already :)
    #
    # Meanwhile Python took until version 3.4 to have a
    # simple html.unescape function.
    try:
        return html.unescape(s)
    except Exception:
        raise Exception('Please use python3.4 or later for this bot.')

def get_quiz_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = payload['results'][0]
    question = result['question']
    letters = ['A', 'B', 'C', 'D']
    random.shuffle(letters)
    correct_letter = letters[0]
    answers = dict()
    answers[correct_letter] = result['correct_answer']
    for i in range(3):
        answers[letters[i+1]] = result['incorrect_answers'][i]
    answers = {
        letter: fix_quotes(answer)
        for letter, answer
        in answers.items()
    }
    quiz = dict(
        question=fix_quotes(question),
        answers=answers,
        answered_options=[],
        pending=True,
        correct_letter=correct_letter,
    )  # type: Dict[str, Any]
    return quiz

def format_quiz_for_markdown(quiz_id: str, quiz: Dict[str, Any]) -> str:
    question = quiz['question']
    answers = quiz['answers']
    answer_list = '\n'.join([
        '* **{letter}** {answer}'.format(
            letter=letter,
            answer=answers[letter],
        )
        for letter in 'ABCD'
    ])
    how_to_respond = '''**reply**: answer {quiz_id} <letter>'''.format(quiz_id=quiz_id)

    content = '''
Q: {question}

{answer_list}
{how_to_respond}'''.format(
        question=question,
        answer_list=answer_list,
        how_to_respond=how_to_respond,
    )
    return content

def update_quiz(quiz: Dict[str, Any], quiz_id: str, bot_handler: Any) -> None:
    bot_handler.storage.put(quiz_id, json.dumps(quiz))

def build_response(is_correct: bool, num_answers: int) -> str:
    if is_correct:
        response = ':tada: **{answer}** is correct, {sender_name}!'
    else:
        if num_answers >= 3:
            response = ':disappointed: WRONG, {sender_name}! The correct answer is **{answer}**.'
        else:
            response = ':disappointed: WRONG, {sender_name}! {option} is not correct.'
    return response

def handle_answer(quiz: Dict[str, Any], option: str, quiz_id: str,
                  bot_handler: Any, sender_name: str) -> Tuple[bool, str]:
    answer = quiz['answers'][quiz['correct_letter']]
    is_new_answer = (option not in quiz['answered_options'])
    if is_new_answer:
        quiz['answered_options'].append(option)

    num_answers = len(quiz['answered_options'])
    is_correct = (option == quiz['correct_letter'])

    start_new_question = quiz['pending'] and (is_correct or num_answers >= 3)
    if start_new_question or is_correct:
        quiz['pending'] = False

    if is_new_answer or start_new_question:
        update_quiz(quiz, quiz_id, bot_handler)

    response = build_response(is_correct, num_answers).format(
        option=option, answer=answer, id=quiz_id, sender_name=sender_name)
    return start_new_question, response


handler_class = TriviaGameHandler
