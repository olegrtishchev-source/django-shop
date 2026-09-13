var mix = {
	methods: {
		// postData() из app.js в catch скрывает тело ответа с ошибкой — а тут
		// как раз нужен конкретный текст валидации (нечётный номер, не только
		// цифры и т.п.), поэтому запрос — напрямую через axios
		submitPayment() {
			const orderId = location.pathname.startsWith('/payment/')
				? Number(location.pathname.replace('/payment/', '').replace(/\/$/, ''))
				: null
			if (orderId === null) return

			axios
				.post(`/api/payment/${orderId}`, { number: this.number1 }, {
					headers: { 'X-CSRFToken': this.getCookie('csrftoken') },
				})
				.then(() => {
					// оплата обрабатывается асинхронно (Celery) — сразу
					// «успешной оплаты» ещё нет, ведём на страницу ожидания
					location.assign(`/progress-payment/${orderId}/`)
				})
				.catch((error) => {
					const message = error?.response?.data?.number?.[0] || 'Ошибка при оплате'
					alert(message)
				})
		}
	},
	data() {
		return {
			number1: '',
			month: '',
			year: '',
			code: '',
			name: '',
		}
	}
}
