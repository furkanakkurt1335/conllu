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
                if xpos == '_':
                    xpos = None
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
            head_token = self.get_token(token.head)
            if head_token:
                token.head = self.get_token(token.head)
            else:
                token.head = None

    def __str__(self):
        return self.text

    def get_token(self, id):
        if id not in self.tokens:
            return False
        return self.tokens[id]

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

    def load_conllu(self, conllu_file):
        if not conllu_file.exists():
            return False
        with conllu_file.open() as f:
            content = f.read()
        sentence_contents = [sentence_content for sentence_content in content.split('\n\n') if sentence_content.strip()]
        for sentence_content in sentence_contents:
            sentence = Sentence(sentence_content)
            self.sentences[sentence.sent_id] = sentence

    def get_sentence(self, id):
        if id not in self.sentences:
            return False
        return self.sentences[id]
