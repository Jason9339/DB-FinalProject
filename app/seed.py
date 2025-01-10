from datetime import datetime, timedelta
from app import db
from app.models import User, Movie, Cinema, Hall, ScreeningTime, Review
import random

def seed_movies():
    movies = [
        Movie(
            title="獅子王：木法沙",
            description="迪士尼最新的經典故事改編同時是2019年《獅子王》的前傳與續集，帶領觀眾回到驕傲之地的過去，當時穆法薩還是個孤兒，被王子塔卡和他的家人收養。如果你不熟悉這段故事，塔卡最終成為了刀疤，我們假設你知道王子和他選擇的兄弟之間隨著時間發生了什麼事。導演巴里·詹金斯將熟悉的聲音和新鮮的聲音結合在一起，講述一個他形容為在平行時間線上發生的故事——這是一種優雅的說法，表示我們也將跟隨辛巴和娜拉，在當今時代養育他們的女兒基亞拉。這部作品將為迪士尼的年度電影畫下句點，並標誌著他們的票房回歸，但目前尚不確定穆法薩是否能夠達到其前作16億美元的票房成績。",
            genre="動畫/冒險",
            release_date="2024-12-05",
            poster_url="/static/images/Mufasa_The_Lion_King_Poster.jpg",
        ),
        Movie(
            title="獵人克萊文",
            description="是一部2024年美國超級英雄電影，改編自漫威漫畫旗下同名反派角色的故事，由哥倫比亞影業與漫威娛樂共同製作，索尼影視娛樂發行。本片為「索尼影業蜘蛛人宇宙」的第六部電影，由J·C·錢德爾執導，阿特·馬庫姆和馬修·霍拉威、李察·威克撰寫劇本，亞倫·強森、亞莉安娜·黛博塞、佛列德·海辛爾、亞歷桑德羅·尼沃拉、克里斯多福·阿伯特和羅素·克洛主演。劇情講述一名俄羅斯裔美國獵人一心想成為世上最偉大的獵人，但因一場打獵意外而使自身產生突變成能力超群的狩獵者。",
            genre="動作/科幻",
            release_date="2024-12-13",
            poster_url="/static/images/Kraven_the_Hunter_Poster.jpg",
        ),
        Movie(
            title="音速小子3",
            description="是一部2024年美國真人動畫奇幻喜劇片，由傑夫·福勒執導，派屈克·凱西、喬許·米勒和約翰·惠廷頓共同編劇。電影改編自SEGA出品的電子遊戲《音速小子》系列，為2022年電影《音速小子2》的續集，由詹姆士·馬斯登、蒂卡·桑普特、娜塔莎·羅斯威爾、亞當·帕利和金·凱瑞主演，班·許瓦茲、柯琳·維拉德、伊卓瑞斯·艾巴和基努·李維配音。",
            genre="動畫/冒險",
            release_date="2024-12-20",
            poster_url="/static/images/Sonic_the_Hedgehog_3_Poster.jpg",
        ),
        Movie(
            title="神鬼戰士II",
            description="在《角鬥士》成為雷德利·斯科特迄今為止最大的電影並開啟羅素·克勞的2000年代後，24年後，斯科特再次回到大銀幕，講述原電影中科莫杜斯的侄子盧修斯·維魯斯二世的故事。在備受期待的續集中，由保羅·梅斯卡爾飾演的盧修斯走上了一條與少年時期激勵過他的男人相似的道路：羅素·克勞飾演的羅馬將軍麥克西姆斯，他曾被盧修斯那位為了權力瘋狂的叔叔奴役，被迫成為角鬥士，後來領導了一場針對皇帝的民眾起義。約瑟夫·奎因和弗雷德·海金格飾演蓋塔和卡拉卡拉，這對共治的皇帝看起來像是終其一生只喝過血（這並非貶低），但所有目光都集中在盧修斯與馬克里努斯之間剛萌芽的關係上，馬克里努斯是丹澤爾·華盛頓飾演的角色，根據真實的羅馬歷史，他在卡拉卡拉死後登上了皇位。然而，當羅馬競技場成為海戰的舞台，且有報導稱梅斯卡爾在銀幕上與一群獅猩作戰時，我們被續集中那些狂野、歷史不準的精彩情節深深吸引。",
            genre="動作/冒險",
            release_date="2024-11-15",
            poster_url="/static/images/Gladiator_II_Poster.jpg",
        ),
        Movie(
            title="海洋奇緣2",
            description="《海洋奇緣》回來了，莫安娜再次與毛伊（道恩·強森）重逢，因為來自祖先的神秘召喚，莫安娜開始了一次新的海上冒險。這部續集是注定的，特別是考慮到《海洋奇緣》成為2023年最受串流平台播放的電影，這對於一部2016年上映的電影來說可謂不錯。奧莉·伊·克拉瓦霍領銜回歸的配音陣容，包括泰穆埃拉·莫里森飾演圖伊酋長、瑞秋·豪斯飾演塔拉奶奶，以及艾倫·圖代克飾演公雞Heihei。",
            genre="動畫/冒險",
            release_date="2024-11-27",
            poster_url="/static/images/Moana_2_poster.jpg",
        ),
        Movie(
            title="紅色一號",
            description="克里斯·埃文斯和道恩·強森終於組成搭檔！我們其實有些驚訝，這兩位大明星花了這麼長時間才合作，對了，我們並不算他們在《秋天的男人》中的客串。由傑克·卡斯丹（《勇敢者遊戲：歡迎來到叢林》）執導的這部奇幻動作喜劇，運用了經典的“異類搭檔”劇情，這次是聖誕老人的安全負責人（強森）與最臭名昭著的賞金獵人（埃文斯）聯手，故事講述聖誕老人被從北極綁架後的冒險。J.K.·西蒙斯、劉玉玲和克里斯托弗·希夫尤也加入了演員陣容。",
            genre="動作/喜劇",
            release_date="2024-11-15",
            poster_url="/static/images/Red_One_Poster.jpg",
        ),
        Movie(
            title="毒王女人夢",
            description="留意佐伊·索尔达娜和卡拉·索菲亚·加斯孔在鏡頭前的合作以及各自的表現，因為導演雅克·奧迪亞爾（Jacques Audiard）在這部電影中巧妙地跨越了多個類型——從歌舞劇、肥皂劇到高強度動作片，並將這一切融為一體，成為一部讓人熱議的作品，預計在11月登陸Netflix。這是索尔达娜的一次體操般的、職業生涯巔峰的表現，而加斯孔則以一位變性女演員的身份，為卡特爾老大這一角色帶來了顛覆性的詮釋，這位老大在上演消失後，再次以真實的自我重新出現。索尔达娜飾演一位墨西哥城的律師，幫助她的新客戶；隨著時間的推移，他們的關係發展為一場致力於國家社會改革的夥伴關係。加斯孔有可能在最佳女演員獎項上創造歷史，我們也不會對當信封打開時聽到她的名字感到驚訝。",
            genre="歌舞/驚悚",
            release_date="2024-5-18",
            poster_url="/static/images/Emilia_Pérez_film_poster.png",
        ),
        Movie(
            title="猛毒最終章：最後一舞",
            description="湯姆·哈迪回歸飾演艾迪·布洛克，為無法被影評左右的《毒液》三部曲畫上句號，帶來一場瘋狂的告別，既是布洛克的，也是他所宿主的共生體的告別。然而，正如導演凱莉·馬塞爾所提醒的那樣，“共生體的故事在這個系列中有很多”，而《最後的舞蹈》則為衍生劇和跨界合作保留了空間。我們不會透露更多細節，只說這部電影雖然沒有任何重磅劇透（你現在應該已經聽過了），但它確實暗示了一個我們以前未曾在銀幕上見過的大型漫威角色。",
            genre="動作/科幻",
            release_date="2024-10-25",
            poster_url="/static/images/Venom_The_Last_Dance_Poster.jpg",
        ),
        Movie(
            title="微笑2",
            description="編劇兼導演帕克·芬恩從一個簡單的點子出發，創作出了2019年驚悚驚悚片《微笑》的意外成功。在續集中，微笑詛咒蔓延開來，一位國際流行歌手（娜歐蜜·斯科特，迪士尼真人版《阿拉丁》中的茉莉公主）在即將開始她的世界巡演時也遭遇了微笑詛咒。《微笑》原作在全球票房賺取了2.17億美元，並成功吸引了大量觀眾，而《微笑2》有望成為萬聖節期間的必看恐怖片，甚至超越前作的票房表現。",
            genre="恐怖/推理",
            release_date="2024-10-18",
            poster_url="/static/images/Smile_2_Poster.jpg",
        ),
        Movie(
            title="荒野機器人",
            description="彼得·布朗的暢銷兒童書籍系列進軍大銀幕，由導演克里斯·桑德斯執導，他曾是迪士尼《莉羅與史迪奇》的編劇兼導演。盧皮塔·尼永’o飾演羅茲，一個在孤島上遇難的機器人，她必須適應這個野性且陌生的環境。電影還有一個全明星配音陣容，包括佩德羅·帕斯卡、凱瑟琳·奧哈拉、馬克·哈米爾等人，他們為島上的生物配音，這些生物最終成為羅茲的收養家庭。",
            genre="動畫/冒險",
            release_date="2024-9-8",
            poster_url="/static/images/The_Wild_Robot_poster.jpg",
        ),
    ]
    return movies


def seed_cinemas():
    cinemas = [
        Cinema(name="大都會影城", location="台北市信義區"),
        Cinema(name="新光影城", location="台北市西門町"),
        Cinema(name="威秀影城", location="台北市信義區"),
    ]

    # 為每個影院加上影廳
    cinemas[0].halls = [
        Hall(name="A1", size=100),
        Hall(name="A2", size=120),
    ]

    cinemas[1].halls = [
        Hall(name="B1", size=110),
        Hall(name="B2", size=130),
    ]

    cinemas[2].halls = [
        Hall(name="C1", size=140),
        Hall(name="C2", size=150),
    ]
    return cinemas


def create_fixed_screening_times(movies, cinemas):
    """為每部電影創建固定場次"""
    screenings = []
    fixed_times = [
        datetime.now().replace(hour=10, minute=0),
        datetime.now().replace(hour=14, minute=0),
        datetime.now().replace(hour=18, minute=0),
    ]
    for i, movie in enumerate(movies):
        for cinema in cinemas:
            for hall in cinema.halls:
                for time in fixed_times:
                    screenings.append(
                        ScreeningTime(
                            movie_id=movie.id,
                            cinema_id=cinema.id,
                            hall_id=hall.id,
                            date=time + timedelta(days=i % 7),
                            price=300 + (i % 5) * 10,
                        )
                    )
    return screenings


def create_admin():
    admin = User(username="admin", email="admin@example.com")
    admin.set_password("admin123")
    return admin


def seed_users():
    users = [
        User(username="user1", email="user1@example.com"),
        User(username="user2", email="user2@example.com"),
        User(username="user3", email="user3@example.com"),
    ]
    for user in users:
        user.set_password("password123")
    return users


def seed_reviews(users, movies):
    reviews = []
    # 為每部電影創建多個評論，確保有足夠的數據來計算平均分
    for movie in movies:
        # 每部電影隨機生成2-5條評論
        num_reviews = random.randint(2, 5)
        for _ in range(num_reviews):
            review = Review(
                user_id=random.choice(users).id,
                movie_id=movie.id,
                content=f"這是一條關於《{movie.title}》的影評。",
                rate=random.uniform(3.0, 5.0)  # 生成3.0到5.0之間的隨機評分
            )
            reviews.append(review)
    return reviews


def init_db():
    """初始化數據庫"""
    if Movie.query.first() is not None:
        return

    # 先添加基礎數據
    movies = seed_movies()
    cinemas = seed_cinemas()
    users = seed_users()
    admin = create_admin()

    db.session.add_all(movies)
    db.session.add_all(cinemas)
    db.session.add_all(users)
    db.session.add(admin)
    db.session.commit()

    # 添加放映場次
    screenings = create_fixed_screening_times(movies, cinemas)
    db.session.add_all(screenings)
    db.session.commit()

    # 最後添加評論，這樣可以觸發評論的事件監聽器
    reviews = seed_reviews(users, movies)
    db.session.add_all(reviews)
    db.session.commit()

    print("資料庫初始化完成！")
