from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://oxford:oxford@instantinopaul.grkjwvv.mongodb.net/?retryWrites=true&w=majority"
db_name = "playpick_db"
cred_collections = "credentials"
user_data = "userwatchlist"


class DB:
    def __init__(self):
        self.client = MongoClient(uri, server_api=ServerApi("1"))

        try:
            self.client.admin.command("ping")
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)

        self.db = self.client[db_name]

        self.cred_client = self.db[cred_collections]
        self.user_data_client = self.db[user_data]

    def get_users(self):
        return [
            doc["user_name"]
            for doc in self.cred_client.find({}, {"_id": 0, "user_name": 1})
        ]

    def create_user(self, user, passw):
        self.cred_client.insert_one({"user_name": user, "password": passw})
        self.user_data_client.insert_one({"user_name": user, "movies": []})

    def validate_passw(self, user, passw):
        return (
            self.cred_client.find_one(
                {"user_name": {"$regex": user}}, {"_id": 0, "password": 1}
            )["password"]
            == passw
        )

    def get_user_movies(self, user):
        return self.user_data_client.find_one(
            {"user_name": {"$regex": user}}, {"_id": 0, "movies": 1}
        ).get("movies", [])

    def add_user_movies(self, user, movies):
        self.user_data_client.update_many(
            {"user_name": {"$regex": user}}, {"$push": {"movies": {"$each": movies}}}
        )


if __name__ == "__main__":
    db = DB()
    # db.create_user("aziz", "aziz")
    print(db.get_users())
    # print(db.validate_passw("sayan", "sayan"))
    db.add_user_movies("aziz", ["db1", "db2"])
    print(db.get_user_movies("aziz"))
