from pathlib import Path
from subprocess import run
import re
import json
import subprocess

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
                feats_sorted_d = dict(sorted(token.feats.items(), key=lambda x: x[0]))
                feats = '|'.join([f'{key}={value}' for key, value in feats_sorted_d.items()])
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
    def __init__(self, name, published=False, version=None, use_gh_cli=None):
        self.name = name
        self.sentences = {}
        self.published = published
        self.version = version
        self.use_gh_cli = use_gh_cli if use_gh_cli is not None else self._check_gh_cli()
        
        if self.published:
            if self.use_gh_cli:
                self._fetch_with_gh_cli()
            else:
                self._fetch_with_git()
    
    def _check_gh_cli(self):
        """Check if GitHub CLI is available and authenticated."""
        try:
            subprocess.run(['gh', 'auth', 'status'], 
                          capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _fetch_with_gh_cli(self):
        """Fetch treebank metadata and files using GitHub CLI."""
        try:
            print(f"Fetching {self.name} with GitHub CLI...")
            
            # Get repository metadata
            cmd = ['gh', 'api', f'repos/UniversalDependencies/{self.name}']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            repo_info = json.loads(result.stdout)
            
            # Get available tags/versions
            cmd = ['gh', 'api', f'repos/UniversalDependencies/{self.name}/tags']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            tags = json.loads(result.stdout)
            
            # Determine version to use
            if self.version:
                # Check if requested version exists
                version_tag = f'r{self.version}'
                if not any(tag['name'] == version_tag for tag in tags):
                    print(f'Warning: Version {self.version} not found, using latest')
                    self.version = None
            
            if not self.version and tags:
                # Use latest version
                latest_tag = tags[0]['name']  # Tags are usually sorted by date
                tag_pattern = re.compile(r'r(\d+\.\d+)')
                tag_search = tag_pattern.search(latest_tag)
                if tag_search:
                    self.version = tag_search.group(1)
            
            # Get directory listing to find .conllu files
            ref = f'r{self.version}' if self.version else repo_info['default_branch']
            url = f'repos/UniversalDependencies/{self.name}/contents?ref={ref}'
            cmd = ['gh', 'api', url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            contents = json.loads(result.stdout)
            
            # Find and download .conllu files
            conllu_files = [item for item in contents if item['name'].endswith('.conllu')]
            
            for file_info in conllu_files:
                print(f"  Downloading {file_info['name']}...")
                cmd = ['gh', 'api', file_info['download_url']]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.load_conllu(result.stdout, data_type='string')
            
            print(f"  Loaded {len(self.sentences)} sentences from {len(conllu_files)} files")
            
        except subprocess.CalledProcessError as e:
            print(f"Error fetching with GitHub CLI: {e}")
            print("Falling back to git clone method...")
            self.use_gh_cli = False
            self._fetch_with_git()
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub API response: {e}")
            print("Falling back to git clone method...")
            self.use_gh_cli = False
            self._fetch_with_git()
    
    def _fetch_with_git(self):
        """Fetch treebank using traditional git clone method."""
        self.clone_treebank()
        self.directory = Path(__file__).parent / 'repos' / self.name
        if self.version:
            self.checkout_version()
        else:
            latest_tag = run(['git', 'describe', '--tags', '--abbrev=0'], capture_output=True, cwd=self.directory).stdout.decode().strip()
            tag_pattern = re.compile(r'r(\d+\.\d+)')
            tag_search = tag_pattern.search(latest_tag)
            if tag_search:
                self.version = tag_search.group(1)
        conllu_files = list(self.directory.glob('*.conllu'))
        for conllu_file in conllu_files:
            self.load_conllu(conllu_file)

    def clone_treebank(self):
        base_url = 'https://github.com/UniversalDependencies/{name}.git'
        script_dir = Path(__file__).parent
        repo_dir = script_dir / 'repos'
        if not repo_dir.exists():
            repo_dir.mkdir()
        tb_dir = repo_dir / self.name
        if not tb_dir.exists():
            run(['git', 'clone', base_url.format(name=self.name), tb_dir])
            print(f'Cloned {self.name} to {tb_dir}.')

    def checkout_version(self):
        if not self.published:
            return False
        tag_pattern = re.compile(r'r(\d+\.\d+)')
        all_tags = run(['git', 'tag', '-l'], capture_output=True, cwd=self.directory).stdout.decode().split('\n')
        version_tags = []
        for tag in all_tags:
            tag_search = tag_pattern.search(tag)
            if tag_search:
                version_tags.append(tag_search.group(1))
        if self.version not in version_tags:
            print(f'Version {self.version} not found in {self.name}.')
            self.version = None
            return False
        run(['git', 'checkout', f'r{self.version}'], cwd=self.directory)
        print(f'Checked out version {self.version} of {self.name}.')
        return True

    def load_conllu(self, data, data_type='file'):
        if data_type == 'file':
            if type(data) == str:
                data = Path(data)
            if not data.exists():
                return False
            with data.open() as f:
                content = f.read()
        elif data_type == 'string':
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
