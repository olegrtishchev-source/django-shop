var mix = {
    computed: {
      tags () {
          if(!this.product?.tags) return []
          return this.product.tags
      }
    },
    methods: {
        changeCount (value) {
            this.count = this.count + value
            if (this.count < 1) this.count = 1
        },
        getProduct() {
            const productId = location.pathname.startsWith('/product/')
            ? Number(location.pathname.replace('/product/', '').replace('/', ''))
            : null
            this.getData(`/api/product/${productId}`).then(data => {
                this.product = {
                    ...this.product,
                    ...data
                }
                if(data.images.length)
                    this.activePhoto = 0
            }).catch(() => {
                this.product = {}
                console.warn('Ошибка при получении товара')
            })
        },
        // Если пользователь авторизован, подставляем его ФИО/email из профиля
        // в форму отзыва — по аналогии с формой оформления заказа (ТЗ, стр. 5:
        // "если пользователь авторизован, то данные выбираются из его профиля
        // автоматически и подставляются в форму"). Для анонимного пользователя
        // /api/profile отвечает 401 — тогда просто ничего не подставляем,
        // форма остаётся как раньше, с пустыми полями.
        prefillReviewFromProfile () {
            this.getData('/api/profile').then(data => {
                this.review.author = data.fullName || ''
                this.review.email = data.email || ''
            }).catch(() => {})
        },
        submitReview () {
            this.postData(`/api/product/${this.product.id}/reviews`, {
                author: this.review.author,
                email: this.review.email,
                text: this.review.text,
                rate: this.review.rate
            }).then(({data}) => {
                this.product.reviews = data
                alert('Отзыв опубликован')
                this.review.author = ''
                this.review.email = ''
                this.review.text = ''
                this.review.rate = 5
            }).catch(() => {
                console.warn('Ошибка при публикации отзыва')
            })
        },
        setActivePhoto(index) {
            this.activePhoto = index
        }
    },
    mounted () {
        this.getProduct();
        this.prefillReviewFromProfile();
    },
    data() {
        return {
            product : {},
            activePhoto: 0,
            count: 1,
            review: {
                author: '',
                email: '',
                text: '',
                rate: 5
            }
        }
    },
}