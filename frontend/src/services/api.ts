import axios from "axios";

export const api = axios.create({
	baseURL: "http://localhost:8000/api/v1",
});

export const setAuthToken = (token: string | null) => {
	if (token) api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
	else delete api.defaults.headers.common["Authorization"];
};

// Ensure token is loaded on startup
setAuthToken(localStorage.getItem("token"));

// Optional: global 401 handling - keep simple (no redirects here)
api.interceptors.response.use(
	(r) => r,
	(error) => {
		return Promise.reject(error);
	}
);
