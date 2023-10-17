from __future__ import annotations
from sqloquent.asyncql import (
    AsyncSqlModel, AsyncRelatedCollection, AsyncRelatedModel,
    async_has_one, async_has_many, async_belongs_to, async_belongs_to_many,
)

class User(AsyncSqlModel):
    table = 'users'
    columns = ('id', 'name')
    friends: AsyncRelatedCollection
    friendships: AsyncRelatedCollection
    avatar: AsyncRelatedModel
    posts: AsyncRelatedCollection

class Avatar(AsyncSqlModel):
    table = 'avatars'
    columns = ('id', 'url', 'user_id')
    user: AsyncRelatedModel

class Post(AsyncSqlModel):
    table = 'posts'
    columns = ('id', 'content', 'user_id')
    author: AsyncRelatedModel

class Friendship(AsyncSqlModel):
    table = 'friendships'
    columns = ('id', 'user1_id', 'user2_id')
    user1: AsyncRelatedModel
    user2: AsyncRelatedModel

    @classmethod
    async def insert(cls, data: dict) -> Friendship | None:
        # also set inverse relationship
        result = await super().insert(data)
        if result:
            await super().insert({
                **data,
                'user1_id': data['user2_id'],
                'user2_id': data['user1_id'],
            })

    @classmethod
    async def insert_many(cls, items: list[dict]) -> int:
        inverse = [
            {
                'user1_id': item['user2_id'],
                'user2_id': item['user1_id']
            }
            for item in items
        ]
        return await super().insert_many([*items, *inverse])

    async def delete(self):
        # first delete the inverse
        await self.query().equal('user1_id', self.data['user2_.id']).equal(
            'user2_id', self.data['user1_id']
        ).delete()
        await super().delete()

User.avatar = async_has_one(User, Avatar)
Avatar.user = async_belongs_to(Avatar, User)

User.posts = async_has_many(User, Post)
Post.author = async_belongs_to(Post, User)

User.friendships = async_has_many(User, Friendship, 'user1_id')
User.friends = async_belongs_to_many(User, User, Friendship, 'user1_id', 'user2_id')

Friendship.user1 = async_belongs_to(Friendship, User, 'user1_id')
Friendship.user2 = async_belongs_to(Friendship, User, 'user2_id')
