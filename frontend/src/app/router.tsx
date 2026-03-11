import { createBrowserRouter, Navigate } from "react-router-dom";

import AppLayout from "../layout/AppLayout";
import Dashboard from "../pages/Dashboard";
import Settings from "../pages/Settings";
import Protected from "../auth/protected";
import LoginRedirect from "../auth/login-redirect";

const router = createBrowserRouter([
	{
		path: "/login",
		element: <LoginRedirect />,
	},
	{
		path: "/",
		element: (
			<Protected>
				<AppLayout />
			</Protected>
		),
		children: [
			{
				index: true,
				element: <Dashboard />,
			},
			{
				path: "settings",
				element: <Settings />,
			},
		],
	},
	{
		path: "*",
		element: <Navigate to="/" replace />,
	},
]);

export default router;
