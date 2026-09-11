var mix = {
	methods: {
		generateRandomNumber() {
			// до 8 цифр; чётное и не оканчивается на 0 — чтобы кнопка
			// «Сгенерировать случайный счёт» по умолчанию давала номер,
			// проходящий фиктивную проверку оплаты (ТЗ, стр. 6)
			const length = 6 + Math.floor(Math.random() * 3) // 6..8 цифр
			let digits = ''
			for (let i = 0; i < length - 1; i++) {
				digits += Math.floor(Math.random() * 10)
			}
			const lastDigitOptions = [2, 4, 6, 8]
			digits += lastDigitOptions[Math.floor(Math.random() * lastDigitOptions.length)]
			this.number1 = digits
		},
		submitPayment() {
			const orderId = location.pathname.startsWith('/payment-someone/')
				? Number(location.pathname.replace('/payment-someone/', '').replace(/\/$/, ''))
				: null
			if (orderId === null) return

			axios
				.post(`/api/payment/${orderId}`, { number: this.number1 }, {
					headers: { 'X-CSRFToken': this.getCookie('csrftoken') },
				})
				.then(() => {
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
		}
	}
}
