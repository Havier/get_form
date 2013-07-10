import re
import types
import sqlite3

def safe_name(value):
    """Validator user name. User name must consist of the following characters a-z A-Z 0-9 - _"""
    error_message = 'Value must consist of only a-z A-Z 0-9 - _ characters'
    if not re.match('^[-\w]+$', value):
        return error_message

def email_validator(value):
    """validator email addresses"""
    error_message = 'Email must be in format username@hostname '
    if not re.match('^[_.0-9a-z-]+@[0-9a-z-]+.[a-z]{2,4}$', value):
        return error_message

def range_validator(value, x, y):
    """Check the value belonging to the interval (x, y)"""
    error_message = 'Value must be in interval (%i,%i) ' % (x, y)
    if not x <= value <= y:
        return error_message

def port_validator(value):
    """Validator port number. 1 <= port number <= 65535"""
    return range_validator(value, 1, 65535)


def ip_validator(value):
    """Validator ip address"""
    error_message = 'IP address must be in format xxx.xxx.xxx.xxx, xxx in interval (0, 255)'
    parts = value.split('.')
    if not len(parts) == 4 or not all(0 <= int(part) < 256 for part in parts):
        return error_message

def host_validator(value):
    """Validator host name"""
    error_message = 'Hostname must be in format some.domain.com'
    if not re.match(r'^([0-9a-z][-\w]*?[0-9a-z].)+[a-z0-9\-]{2,15}$', value):
        return error_message

def empty_validator(value):
    """Verification of presence of value. Return error if blank not empty"""
    error_message = 'Blank not empty '
    if value:
        return error_message

def not_blank(value):
    """Verification of presence of value. Return error if blank is empty"""
    error_message = 'Blank is empty '
    if not value:
        return error_message

def or_filter(*func):
    """Return error if all functions returned error"""
    def wrap(arg):
        error_message = ''
        for f in func:
            if f(arg):
                error_message = f(arg)
            else:
                return None
        return error_message
    return wrap

def and_filter(*func):
    """Return error if any functions returned error"""
    def wrap(arg):
        error_message = ''
        for f in func:
            if f(arg):
                return error_message + f(arg)
            else:
                return None
    return wrap

def validate_together(*args, **func):
    """Return result of the function 'func' with arguments 'args'"""
    def validate_together_value(value):
        arg_list = []
        for item in args:
            if value.has_key(item):
                arg_list.append(value[item])
            else:
                return '"%s" cannot be blank' %(item)
        return func['func'](*arg_list)
    return validate_together_value

def create_class(cursor, form_link):
    """create class method"""
    form_class = type(str(form_link), (BaseForm, ), {'cursor': cursor})
    cur = cursor.execute('SELECT id, validator FROM questions WHERE form_id =(SELECT id FROM forms WHERE link = ?)', [form_link])
    validator = cur.fetchall()
    local_vars = locals()
    for (id, validator_name) in validator:
        if validator_name in local_vars:
            setattr(form_class, 'question_%s'%(id,), local_vars[validator_name])
    return form_class

class BaseForm(object):
    """parent class"""

    form_link = ''
    answer_list = []
    answer_data = {}
    errors = {}
    clean_data = {}

    # get form name from the database
    def get_form_name(self):
      cur = self.cursor.execute('SELECT name FROM forms WHERE link = ?', [self.form_link])
    	return cur.fetchone()
    
    # get questions name from the database
    def get_questions(self):
    	cur = self.cursor.execute('SELECT id, question, answer_type, required FROM questions WHERE form_id =(SELECT id FROM forms WHERE link = ?)',
        	[self.form_link])
    	questions = cur.fetchall()
    	form_question = {}
    	for item in questions:
        	cur = self.cursor.execute('SELECT variant FROM variants WHERE question_id = (?)', [item[0]])
        	variants = cur.fetchall()
        	form_question['question_'+str(item[0])] = dict({
                          'q_text': item[1],
                          'q_type': item[2],
                          'q_required': item[3],
                          'q_variants': variants})
        self.answer_list = form_question.keys()
        return form_question

    # validation
    def is_valid(self, form):
        self.errors.clear()
        self.answer_data.clear()
        for item in self.answer_list:
            if item in form.keys() and form[item]:
                if len(form.getlist(item)) > 1:
                    self.answer_data[item] = form.getlist(item)
                else:
                    self.answer_data[item] = form[item]    
            else:
                self.answer_data[item] = ''
            print self.answer_data     
        for key, arg in self.__class__.__dict__.items():
            if type(arg) == types.FunctionType:
                if arg.func_name == 'validate_together_value':
                    if arg(self.answer_data):
                        self.errors[key] = arg(self.answer_data)
                elif not self.answer_data.has_key(key):
                    self.errors[key] = 'Value cannot be blank'
                else:
                    if arg(self.answer_data[key]):
                        self.errors[key] = arg(self.answer_data[key])
        if self.errors:
            return False
        else:
            self.clean_data = self.answer_data
            answers = []
            for answer in self.clean_data:
                for var_answer in self.clean_data[answer]:
                    answers.append((var_answer, answer[9:]))
            self.cursor.executemany('INSERT INTO answers (answer, question_id) VALUES (?, ?)',
                        answers)
            self.cursor.commit()
            return True
