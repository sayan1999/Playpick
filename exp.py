# importing the module
import imdb

# creating instance of IMDb
ia = imdb.IMDb()

# id
code = "0275669"

# getting information
series = ia.get_movie(code)

# getting cover url of the series
cover = series.data["cover url"]

# printing the object i.e name
print(f"series{series=}")

# print the cover
print(cover)
