import { createBrowserRouter, Navigate } from "react-router-dom";

import AppLayout from "../layout/AppLayout";
import Dashboard from "../pages/Dashboard";
import Settings from "../pages/Settings";
import Backtest from "../pages/Backtest";
import Data from "../pages/Data";
import DataDetail from "../pages/DataDetail";
import LiveLong from "../pages/LiveLong";
import LiveMedium from "../pages/LiveMedium";
import LiveShort from "../pages/LiveShort";
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
			{
				path: "analysis/backtest",
				element: <Backtest />,
			},
			{
				path: "analysis/data",
				element: <Data />,
			},
			{
				path: "analysis/data/:id",
				element: <DataDetail />,
			},
			{
				path: "live/long",
				element: <LiveLong />,
			},
			{
				path: "live/medium",
				element: <LiveMedium />,
			},
			{
				path: "live/short",
				element: <LiveShort />,
			},
		],
	},
	{
		path: "*",
		element: <Navigate to="/" replace />,
	},
]);

export default router;
