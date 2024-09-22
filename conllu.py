from pathlib import Path
import re
from subprocess import run

class Token:
    def __init__(self, id, form, lemma, upos, xpos,
                 feats, head, deprel, deps, misc):
        self.id, self.form, self.lemma, self.upos, self.xpos = id, form, lemma, upos, xpos
        self.feats, self.head, self.deprel, self.deps, self.misc = feats, head, deprel, deps, misc

    def __str__(self):
        return self.form

metadata_pattern = re.compile(r'#\s*(\S+)\s*=\s*(.+)$')
token_pattern = re.compile(r'(?:.+\t){9}(?:.+)$')
id_pattern = re.compile(r'^\d+(?:-\d+)?$')

class Sentence:
    def __init__(self, content):
        self.tokens = {}
        self.sent_id, self.text, self.metadata = None, None, None
        for line in content.split('\n'):
            metadata_search = metadata_pattern.search(line)
            if metadata_search:
                key, value = metadata_search.groups()
                if key == 'sent_id':
                    self.sent_id = value
                elif key == 'text':
                    self.text = value
                else:
                    if not self.metadata:
                        self.metadata = {}
                    self.metadata[key.strip()] = value.strip()
            elif token_pattern.match(line):
                fields = line.split('\t')
                id, form, lemma, upos, xpos, feats_str, head, deprel, deps, misc = fields
                if not id_pattern.match(id):
                    print(f'Invalid token id: {id} in sentence {self.sent_id}. Skipping sentence.')
                    continue
                if upos == '_':
                    upos = None
                if xpos == '_':
                    xpos = None
                if head == '_':
                    head = None
                if deprel == '_':
                    deprel = None
                if deps == '_':
                    deps = None
                if misc == '_':
                    misc = None
                feats = None
                if feats_str != '_':
                    feats = {}
                    if '|' in feats_str:
                        for feat in feats_str.split('|'):
                            key, value = feat.split('=')
                            feats[key] = value
                token = Token(id, form, lemma, upos, xpos, feats, head, deprel, deps, misc)
                self.tokens[id] = token
        for token in self.tokens.values():
            token.head = self.get_token(token.head)

    def __str__(self):
        return self.text

    def get_token(self, id):
        if id not in self.tokens:
            return None
        return self.tokens[id]

    def get_conllu(self):
        conllu = ''
        if self.sent_id:
            conllu += f'# sent_id = {self.sent_id}\n'
        if self.text:
            conllu += f'# text = {self.text}\n'
        if self.metadata:
            for key, value in self.metadata.items():
                conllu += f'# {key} = {value}\n'
        for token in self.tokens.values():
            id, form, lemma, upos, xpos = token.id, token.form, token.lemma, token.upos, token.xpos
            if not id:
                id = '_'
            if not form:
                form = '_'
            if not lemma:
                lemma = '_'
            if not upos:
                upos = '_'
            if not xpos:
                xpos = '_'
            conllu += f'{id}\t{form}\t{lemma}\t{upos}\t{xpos}\t'
            feats = '_'
            if token.feats:
                feats = '|'.join([f'{key}={value}' for key, value in token.feats.items()])
            conllu += f'{feats}\t'
            head = '_'
            if token.head:
                head = token.head.id
            elif '-' in token.id:
                head = '_'
            elif '-' not in token.id:
                head = '0'
            deprel, deps, misc = token.deprel, token.deps, token.misc
            if not deprel:
                deprel = '_'
            if not deps:
                deps = '_'
            if not misc:
                misc = '_'
            conllu += f'{head}\t{deprel}\t{deps}\t{misc}\n'
        conllu += '\n'
        return conllu

    def print_conllu(self):
        print(self.get_conllu())

class Treebank:
    def __init__(self, name, published=False):
        self.name = name
        self.sentences = {}
        self.published = published
        if published:
            self.clone_treebank()

    def clone_treebank(self):
        base_url = 'https://github.com/UniversalDependencies/{repo}.git'
        script_dir = Path(__file__).parent
        repo_dir = script_dir / 'repos'
        if not repo_dir.exists():
            repo_dir.mkdir()
        tb_dir = repo_dir / self.name
        if not tb_dir.exists():
            run(['git', 'clone', base_url.format(repo=self.name), tb_dir])
        conllu_files = list(tb_dir.glob('*.conllu'))
        for conllu_file in conllu_files:
            self.load_conllu(conllu_file)

    def load_conllu(self, data, type='file'):
        if type == 'file':
            if type(data) == str:
                data = Path(data)
            if not data.exists():
                return False
            with data.open() as f:
                content = f.read()
        elif type == 'string':
            content = data
        sentence_contents = [sentence_content for sentence_content in content.split('\n\n') if sentence_content.strip()]
        for sentence_content in sentence_contents:
            sentence = Sentence(sentence_content)
            self.sentences[sentence.sent_id] = sentence

    def get_sentence(self, id):
        if id not in self.sentences:
            return False
        return self.sentences[id]

    def save_conllu(self, conllu_file=None):
        if not conllu_file:
            out_file = f'{self.name}.conllu'
        else:
            out_file = conllu_file
        with out_file.open('w') as f:
            for sentence in self.sentences.values():
                f.write(sentence.get_conllu())

    def add_sentence(self, sentence):
        self.sentences[sentence.sent_id] = sentence
