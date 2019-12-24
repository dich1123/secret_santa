from flask import Flask, url_for, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import random
import copy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///santa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ecjhvlekrvbgwkefvblwk34567281ehjdso2n'
db = SQLAlchemy(app)


class Choose(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_name = db.Column(db.String, nullable=False)
    player = db.Column(db.String, nullable=False)
    forbidden_names = db.Column(db.String, nullable=True)

    def __init__(self, game_name, player, forbidden_names):
        self.player = player
        self.game_name = game_name
        self.forbidden_names = forbidden_names

    def __repr__(self):
        return f'Game_name:{self.game_name},Player:{self.player},Forbidden_names:{self.forbidden_names}'


class ChooseDone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_name = db.Column(db.String, nullable=False)
    player = db.Column(db.String, nullable=False)
    choosed_player = db.Column(db.String, nullable=False)

    def __init__(self, game_name, player, choosed_player):
        self.player = player
        self.game_name = game_name
        self.choosed_player = choosed_player

    def __repr__(self):
        return f'Game_name:{self.game_name},Player:{self.player},Choosed_player:{self.choosed_player}'


#  info1 = {'a': {'game': 'game', 'forbidden_players': {'a', 'b', 'c'}}, 'b': {'game': 'game', 'forbidden_players': {'a', 'b'}}, 'c': {'game': 'game', 'forbidden_players': {'d', 'c'}}, 'd': {'game': 'game', 'forbidden_players': {'d', 'c'}}, 'e': {'game': 'game', 'forbidden_players': {'e'}}}


def crete_choose_done(info):
    list_info = []
    set_players = set()
    for i in info.keys():
        list_info.append([i, info[i]])
        set_players.add(i)
    list_info = sorted(list_info, key=lambda x: len(x[1]['forbidden_players']), reverse=True)
    ch = 0
    stop = False

    while not stop:
        try:
            game_choosed = {}
            for i in list_info:
                move_set = copy.copy(set_players)
                for j in i[1]['forbidden_players']:
                    move_set.difference_update(j)
                player = random.choice(list(move_set))
                game_choosed[i[0]] = player
                set_players.difference_update(player)
            stop = True
        except IndexError:
            ch += 1
            if ch >= 10:
                return False
    game_choosed['game_name'] = list_info[0][1]['game']
    return game_choosed


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        game_name = request.form['game_name']

        if not game_name:
            flash('Hey! Enter your Game Name please)')
            return redirect(url_for('index'))

        game_name = game_name.lower()
        players = db.engine.execute(f"select player, choosed_player"
                                    f" from choose_done where game_name='{game_name}'").fetchall()
        if not players:
            flash("Sorry( We can't find your game... Try again:')")
            return redirect(url_for('index'))
        return redirect(url_for('choose_yourself', game_name=game_name))

    return render_template('index.html')


@app.route('/choose_yourself/<game_name>', methods=['GET', 'POST'])
def choose_yourself(game_name):
    players = db.engine.execute(f"select player, choosed_player"
                                f" from choose_done where game_name='{game_name}'").fetchall()
    if request.method == 'POST':
        name = request.form['player']
        name = game_name + '&' + name
        return redirect(url_for('show_santa', name=name))
    return render_template('choose_yourself.html', players=players)


@app.route('/santa/<name>')
def show_santa(name):
    person_information = name.split('&')
    game_name = person_information[0]
    players = db.engine.execute(f"select player, choosed_player"
                                f" from choose_done where game_name='{game_name}'").fetchall()
    person = []
    for i in players:
        if i[0] == person_information[1].lower():
            person = i
    return render_template('show_santa.html', person=person)


@app.route('/new', methods=['GET', 'POST'])
def new_secret_santa():
    if request.method == 'POST':
        game_name = request.form['game_name']
        players = request.form['players']
        forbidden_players = request.form['forbidden_players']
        info = [game_name, players]

        if '' in info:
            flash('Game Name and Players must be filled')
            return redirect(url_for('new_secret_santa'))

        games = db.engine.execute('select distinct game_name from choose;').fetchall()
        if not games:
            games.append([' '])
        all_games = []
        for i in games:
            all_games.append(i[0])
        if game_name.lower() in all_games:
            flash('Please Enter enter another Game Name')
            return redirect(url_for('new_secret_santa'))

        dict_info = {}
        for i in players.split(','):
            dict_info[i.strip().lower()] = {'game': game_name.strip().lower(), 'forbidden_players': set(i.strip().lower())}
            for j in forbidden_players.split(';'):
                names = j.split(',')
                names = list(map(lambda x: x.strip().lower(), names))
                if i.strip().lower() in names:
                    for name in names:
                        dict_info[i.strip().lower()]['forbidden_players'].add(name)

        for i in dict_info.keys():
            new_elem = Choose(dict_info[i]['game'], i, ' '.join(dict_info[i]['forbidden_players']))

            try:
                db.session.add(new_elem)
                db.session.commit()
            except:
                flash(f'Were problems with adding{new_elem}')
                print('error db.add in new_secret_santa')
                return redirect(url_for('new_secret_santa'))

        game_choosed = crete_choose_done(dict_info)
        if not game_choosed:
            flash("We can't create game with your settings")
            return redirect(url_for('new_secret_santa'))

        for i in game_choosed.keys():
            if i != 'game_name':
                try:
                    choose = ChooseDone(game_choosed['game_name'], i, game_choosed[i])
                    db.session.add(choose)
                    db.session.commit()
                except:
                    flash('Were problems with creating game')
                    print('error db.add in new_secret_santa choosedone')
                    return redirect(url_for('new_secret_santa'))

        return redirect(url_for('index'))

    return render_template('new_game.html')


if __name__ == '__main__':
    app.run(port=5001, debug=True)
