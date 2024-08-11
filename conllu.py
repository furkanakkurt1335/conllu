import re

class Token:
    def __init__(self, id, form, lemma, upos, xpos, feats, head, deprel, deps, misc):
        self.id = id
        self.form = form
        self.lemma = lemma
        self.upos = upos
        self.xpos = xpos
        self.feats = feats
        self.head = head
        self.deprel = deprel
        self.deps = deps
        self.misc = misc

metadata_pattern = re.compile(r'#\s*(\S+)\s*=\s*(.+)$')
token_pattern = re.compile(r'(?:.+\t){9}(?:.+)$')

class Sentence:
    def __init__(self, content):
        self.tokens = {}
        self.sent_id = None
        self.text = None
        self.metadata = {}
        for line in content.split('\n'):
            metadata_search = metadata_pattern.search(line)
            if metadata_search:
                key, value = metadata_search.groups()
                if key == 'sent_id':
                    self.sent_id = value
                elif key == 'text':
                    self.text = value
                else:
                    self.metadata[key.strip()] = value.strip()
            elif token_pattern.match(line):
                fields = line.split('\t')
                id, form, lemma, upos, xpos, feats_str, head, deprel, deps, misc = fields
                feats = {}
                if '|' in feats_str:
                    for feat in feats_str.split('|'):
                        key, value = feat.split('=')
                        feats[key] = value
                token = Token(id, form, lemma, upos, xpos, feats, head, deprel, deps, misc)
                self.tokens[id] = token
        for token in self.tokens.values():
            head_token = self.get_token(token.head)
            if head_token:
                token.head = self.get_token(token.head)

    def get_token(self, id):
        for token_id, token in self.tokens.items():
            if token_id == id:
                return token

class Treebank:
    def __init__(self, name):
        self.name = name
        self.sentences = {}

    def load_conllu(self, conllu_file):
        with conllu_file.open() as f:
            content = f.read()
        sentence_contents = [sentence_content for sentence_content in content.split('\n\n') if sentence_content.strip()]
        for sentence_content in sentence_contents:
            sentence = Sentence(sentence_content)
            self.sentences[sentence.sent_id] = sentence
    
    def get_sentence(self, id):
        return self.sentences[id]
