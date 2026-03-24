import { useMemo, useState } from "react";
import { Layout, Menu, Dropdown } from "antd";
import {
	MenuFoldOutlined,
	MenuUnfoldOutlined,
	DashboardOutlined,
	SettingOutlined,
	LogoutOutlined,
	RadarChartOutlined,
	GlobalOutlined,
	DatabaseOutlined,
	PlayCircleOutlined,
	LineChartOutlined,
	RiseOutlined,
	DollarOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import { useDispatch } from "react-redux";
import { logout } from "../features/auth/reducer";

const { Header, Sider, Content } = Layout;

const LEAF_KEYS = [
	"/",
	"/analysis/data",
	"/analysis/backtest",
	"/live/long",
	"/live/medium",
	"/live/short",
	"/settings",
];

function getSelectedKey(pathname: string): string {
	return (
		LEAF_KEYS.filter((k) => pathname === k || pathname.startsWith(k + "/"))
			.sort((a, b) => b.length - a.length)[0] ?? "/"
	);
}

function getPageTitle(pathname: string): string {
	if (pathname === "/") return "Dashboard";
	if (/^\/analysis\/backtest\/\d+\/runs\/\d+$/.test(pathname)) {
		const parts = pathname.split("/");
		return `Backtest #${parts[3]} — Run #${parts[5]}`;
	}
	if (/^\/analysis\/backtest\/\d+$/.test(pathname))
		return `Backtest #${pathname.split("/").pop()}`;
	if (pathname === "/analysis/backtest") return "Backtests";
	if (/^\/analysis\/data\/.+$/.test(pathname))
		return pathname.split("/").pop() ?? "Data";
	if (pathname === "/analysis/data") return "Data";
	if (pathname === "/live/long") return "Live — Long";
	if (pathname === "/live/medium") return "Live — Medium";
	if (pathname === "/live/short") return "Live — Short";
	if (pathname === "/settings") return "Settings";
	return "";
}

function AppLayout() {
	const [collapsed, setCollapsed] = useState(false);
	const [isMobile, setIsMobile] = useState(false);
	const navigate = useNavigate();
	const location = useLocation();
	const dispatch = useDispatch();

	const selectedKey = useMemo(
		() => getSelectedKey(location.pathname),
		[location.pathname]
	);

	const pageTitle = useMemo(
		() => getPageTitle(location.pathname),
		[location.pathname]
	);

	const items = useMemo(
		() => [
			{ key: "/", icon: <DashboardOutlined />, label: "Dashboard" },
			{
				key: "/analysis",
				icon: <RadarChartOutlined />,
				label: "Analysis",
				children: [
					{ key: "/analysis/data", icon: <DatabaseOutlined />, label: "Data" },
					{ key: "/analysis/backtest", icon: <PlayCircleOutlined />, label: "Backtest" },
				],
			},
			{
				key: "/live",
				icon: <LineChartOutlined />,
				label: "Live",
				children: [
					{ key: "/live/long", icon: <GlobalOutlined />, label: "Long" },
					{ key: "/live/medium", icon: <DollarOutlined />, label: "Medium" },
					{ key: "/live/short", icon: <RiseOutlined />, label: "Short" },
				],
			},
			{ key: "/settings", icon: <SettingOutlined />, label: "Settings" },
		],
		[]
	);

	const userMenu = {
		items: [
			{
				key: "logout",
				icon: <LogoutOutlined />,
				label: "Logout",
				onClick: () => dispatch(logout()),
			},
		],
	};

	return (
		<Layout className="min-h-screen">
			<Sider
				collapsible
				collapsed={collapsed}
				trigger={null}
				breakpoint="lg"
				collapsedWidth={isMobile ? 0 : 80}
				onBreakpoint={(broken) => {
					setIsMobile(broken);
					setCollapsed(broken);
				}}
			>
				<div className="h-16 flex items-center justify-center text-white font-bold select-none">
					{collapsed ? "QQ" : "Querior Quant"}
				</div>
				<Menu
					theme="dark"
					mode="inline"
					selectedKeys={[selectedKey]}
					defaultOpenKeys={["/analysis", "/live"]}
					items={items}
					onClick={(e) => navigate(e.key)}
				/>
			</Sider>
			<Layout>
				<Header className="bg-white shadow flex items-center justify-between px-4">
					<div className="flex items-center gap-3">
						<button
							className="text-xl p-2 rounded hover:bg-gray-100"
							onClick={() => setCollapsed((v) => !v)}
							aria-label="Toggle menu"
						>
							{collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
						</button>
						<div className="flex items-center gap-2">
							<div className="w-7 h-7 rounded bg-gray-900 text-white flex items-center justify-center font-bold text-xs">
								QQ
							</div>
							<span className="font-semibold hidden sm:block">Querior Quant</span>
							{pageTitle && (
								<>
									<span className="text-gray-300 hidden sm:block">—</span>
									<span className="text-gray-600 hidden sm:block">{pageTitle}</span>
								</>
							)}
						</div>
					</div>
					<Dropdown menu={userMenu} placement="bottomRight" trigger={["click"]}>
						<button className="px-3 py-1 border rounded hover:bg-gray-50">
							Account
						</button>
					</Dropdown>
				</Header>
				<Content>
					<Outlet />
				</Content>
			</Layout>
		</Layout>
	);
}

export default AppLayout;
