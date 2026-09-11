var mix = {
	methods: {
		checkPaymentStatus() {
			const orderId = location.pathname.startsWith('/progress-payment/')
				? Number(location.pathname.replace('/progress-payment/', '').replace(/\/$/, ''))
				: null
			if (orderId === null) return

			this.getData(`/api/order/${orderId}`)
				.then((data) => {
					// пока Celery-таск не отработал, заказ остаётся в
					// статусе «обрабатывается» — опрашиваем дальше
					if (data.status === 'processing') {
						setTimeout(this.checkPaymentStatus, 1500)
						return
					}
					// /order-detail/ — просмотр уже оформленного заказа,
					// без возможности изменения (ТЗ, стр. 6); /orders/ —
					// это форма ОФОРМЛЕНИЯ, сюда вести после оплаты не нужно
					location.assign(`/order-detail/${orderId}/`)
				})
				.catch(() => {
					setTimeout(this.checkPaymentStatus, 1500)
				})
		}
	},
	mounted() {
		this.checkPaymentStatus()
	},
}
