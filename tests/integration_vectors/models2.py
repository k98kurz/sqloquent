from __future__ import annotations
from sqloquent import (
    SqlModel, RelatedCollection, RelatedModel,
    has_one, has_many, belongs_to, belongs_to_many,
)

class User(SqlModel):
    table = 'users'
    columns = ('id', 'name')
    friends: RelatedCollection
    friendships: RelatedCollection
    avatar: RelatedModel
    posts: RelatedCollection

class Avatar(SqlModel):
    table = 'avatars'
    columns = ('id', 'url', 'user_id')
    user: RelatedModel

class Post(SqlModel):
    table = 'posts'
    columns = ('id', 'content', 'user_id')
    author: RelatedModel

class Friendship(SqlModel):
    table = 'friendships'
    columns = ('id', 'user1_id', 'user2_id')
    user1: RelatedModel
    user2: RelatedModel

    @classmethod
    def insert(cls, data: dict) -> Friendship | None:
        # also set inverse relationship
        result = super().insert(data)
        if result:
            super().insert({
                **data,
                'user1_id': data['user2_id'],
                'user2_id': data['user1_id'],
            })

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        inverse = [
            {
                'user1_id': item['user2_id'],
                'user2_id': item['user1_id']
            }
            for item in items
        ]
        return super().insert_many([*items, *inverse])

    def delete(self):
        # first delete the inverse
        self.query().equal('user1_id', self.data['user2_.id']).equal(
            'user2_id', self.data['user1_id']
        ).delete()
        super().delete()

User.avatar = has_one(User, Avatar)
Avatar.user = belongs_to(Avatar, User)

User.posts = has_many(User, Post)
Post.author = belongs_to(Post, User)

User.friendships = has_many(User, Friendship, 'user1_id')
User.friends = belongs_to_many(User, User, Friendship, 'user1_id', 'user2_id')

Friendship.user1 = belongs_to(Friendship, User, 'user1_id')
Friendship.user2 = belongs_to(Friendship, User, 'user2_id')
