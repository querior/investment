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
} from "@ant-design/icons";
import { useNavigate, Outlet } from "react-router-dom";
import { useDispatch } from "react-redux";
import { logout } from "../features/auth/reducer";

const { Header, Sider, Content } = Layout;

function AppLayout() {
	const [collapsed, setCollapsed] = useState(false);
	const navigate = useNavigate();
	const dispatch = useDispatch();
	const [isMobile, setIsMobile] = useState(false);

	const items = useMemo(
		() => [
			{ key: "/", icon: <DashboardOutlined />, label: "Dashboard" },
			{
				key: "/analysis",
				icon: <RadarChartOutlined />,
				label: "Analysis",
				children: [
					{ key: "/analysis/data", icon: <DatabaseOutlined />, label: "Data" },
					{
						key: "/analysis/scenarios",
						icon: <GlobalOutlined />,
						label: "Scenarios",
					},
				],
			},
			{
				key: "/playbook",
				icon: <PlayCircleOutlined />,
				label: "Playbook",
				children: [],
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
					selectedKeys={[location.pathname]}
					items={items}
					onClick={(e) => navigate(e.key)}
				/>
			</Sider>
			<Layout>
				<Header className="bg-white shadow flex items-center justify-between px-4">
					<div className="flex items-center gap-3">
						{/* Always present toggle (works also on desktop) */}
						<button
							className="text-xl p-2 rounded hover:bg-gray-100"
							onClick={() => setCollapsed((v) => !v)}
							aria-label="Toggle menu"
						>
							{collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
						</button>
						<div className="flex items-center gap-2">
							<div className="w-7 h-7 rounded bg-gray-900 text-white flex items-center justify-center font-bold">
								QQ
							</div>
							<div className="font-semibold hidden sm:block">Querior Quant</div>
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
