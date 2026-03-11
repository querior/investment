import { Navigate } from "react-router-dom";
import { useSelector } from "react-redux";
import { RootState } from "../store/reducers";
import Login from "../pages/Login";

function LoginRedirect() {
	const token = useSelector((state: RootState) => state.auth.token);

	return token ? <Navigate to="/" replace /> : <Login />;
}

export default LoginRedirect;
