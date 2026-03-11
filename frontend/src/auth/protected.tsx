import { Navigate, useLocation } from "react-router-dom";
import { useSelector } from "react-redux";
import { RootState } from "../store/reducers";

type Props = {
	children: React.ReactNode;
};

export default function Protected({ children }: Props) {
	const token = useSelector((state: RootState) => state.auth.token);
	const location = useLocation();

	if (!token) {
		return <Navigate to="/login" replace state={{ from: location }} />;
	}

	return <>{children}</>;
}
