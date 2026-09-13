var mix = {
	methods: {
		signUp () {
			const name = document.querySelector('#name').value
			const username = document.querySelector('#login').value
			const password = document.querySelector('#password').value
			this.postData('/api/sign-up', JSON.stringify({ name, username, password }))
				.then(({ data, status }) => {
					location.assign(`/`)
				})
				.catch((error) => {
					const detail = error?.response?.data?.detail
					alert(Array.isArray(detail) ? detail.join('\n') : (detail || 'Ошибка авторизации!'))
				})
		}
	},
	mounted() {
	},
	data() {
		return {}
	}
}