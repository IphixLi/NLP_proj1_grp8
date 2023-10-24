from imdb import Cinemagoer

# create an instance of the Cinemagoer class
ia = Cinemagoer()


if __name__ == '__main__':
    persons = ia.search_person('Bryan Cranston')
    for p in persons:
        print(p.summary())