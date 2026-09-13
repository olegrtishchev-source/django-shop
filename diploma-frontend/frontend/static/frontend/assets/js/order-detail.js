var mix = {
	methods: {
		getOrder(orderId) {
			if(typeof orderId !== 'number') return
			this.getData(`/api/order/${orderId}`)
				.then(data => {
					this.orderId = data.id
					this.createdAt = data.createdAt
					this.fullName = data.fullName
					this.phone = data.phone
					this.email = data.email
					this.deliveryType = data.deliveryType
					this.city = data.city
					this.address = data.address
					this.paymentType = data.paymentType
					this.status = data.status
					this.statusDisplay = data.statusDisplay
					this.totalCost = data.totalCost
					this.products = data.products
					this.comment = data.comment || ''
					if (typeof data.paymentError !== 'undefined') {
						this.paymentError = data.paymentError
					}
				})
		},
		// Отдельный от postData() запрос: postData() в своём catch скрывает
		// тело ответа с ошибкой (error.response.data), а тут как раз нужен
		// текст конкретной ошибки от сериализатора (например ТЗ-шный текст
		// про уже существующий email), а не обезличенный alert.
		register() {
			return axios
				.post(`/api/order/${this.orderId}/register`, {
					fullName: this.fullName,
					email: this.email,
					phone: this.phone,
					password: this.password,
					passwordConfirm: this.passwordConfirm,
				}, {
					headers: { 'X-CSRFToken': this.getCookie('csrftoken') },
				})
		},
		confirmOrder() {
			if (this.orderId === null) return

			const doConfirm = () => {
				this.postData(`/api/order/${this.orderId}`, { ...this })
					.then(({ data: { orderId } }) => {
						alert('Заказ подтвержден')
						const target = this.paymentType === 'someone'
							? `/payment-someone/${orderId}/`
							: `/payment/${orderId}/`
						location.replace(target)
					})
					.catch(() => {
						console.warn('Ошибка при подтверждения заказа')
					})
			}

			// пароль заполнен только в форме для незарегистрированного
			// покупателя (см. order.html) — значит перед подтверждением
			// заказа его сначала нужно зарегистрировать и привязать заказ
			// к новому пользователю
			if (this.password) {
				this.register()
					.then(doConfirm)
					.catch((error) => {
						const data = error?.response?.data || {}
						const message = data.email?.[0] || data.passwordConfirm?.[0] || 'Не удалось зарегистрироваться'
						alert(message)
						if (data.email) {
							// email уже занят — конкретно эта ошибка ТЗ
							// требует предложить войти, а не регистрироваться повторно
							this.showLoginPopup = true
						}
					})
				return
			}

			doConfirm()
		},
		login() {
			this.postData('/api/sign-in', JSON.stringify({
				username: this.loginUsername,
				password: this.loginPassword,
			}))
				.then(() => {
					// после входа данные пользователя должны подставиться в
					// форму (ТЗ) — простой способ этого добиться — перечитать
					// страницу: серверный `user.is_authenticated` и GET
					// /api/order/{id} после этого уже вернут авторизованные данные
					location.reload()
				})
				.catch(() => {
					alert('Неверный логин или пароль')
				})
		}
	},
	mounted() {
		// один и тот же mixin используется и на странице оформления заказа
		// (/orders/<id>/ — order.html), и на странице просмотра уже
		// оформленного заказа (/order-detail/<id>/ — oneorder.html)
		let rawOrderId = null
		if (location.pathname.startsWith('/orders/')) {
			rawOrderId = location.pathname.replace('/orders/', '').replace(/\/$/, '')
		} else if (location.pathname.startsWith('/order-detail/')) {
			rawOrderId = location.pathname.replace('/order-detail/', '').replace(/\/$/, '')
		}
		if (rawOrderId !== null && rawOrderId.length) {
			this.orderId = Number(rawOrderId)
			this.getOrder(this.orderId)
		}
	},
	data() {
		return {
			orderId: null,
			createdAt: null,
			fullName: null,
			phone: null,
			email: null,
			deliveryType: null,
			city: null,
			address: null,
			paymentType: null,
			status: null,
			statusDisplay: null,
			totalCost: null,
			products: [],
			paymentError: null,
			comment: '',
			password: '',
			passwordConfirm: '',
			showLoginPopup: false,
			loginUsername: '',
			loginPassword: '',
		}
	},
}
