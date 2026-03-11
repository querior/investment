import { Card, Typography } from "antd";
import { Link } from "react-router-dom";
import {
	RiseOutlined,
	DollarOutlined,
	GlobalOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;

const layers = [
	{
		key: "long",
		label: "Long",
		description: "Macro — allocazione strategica del capitale",
		icon: <GlobalOutlined className="text-2xl" />,
		color: "#1677ff",
	},
	{
		key: "medium",
		label: "Medium",
		description: "Reddito — flusso costante e prevedibile",
		icon: <DollarOutlined className="text-2xl" />,
		color: "#52c41a",
	},
	{
		key: "short",
		label: "Short",
		description: "Trading — vantaggio statistico su movimenti di mercato",
		icon: <RiseOutlined className="text-2xl" />,
		color: "#fa8c16",
	},
];

export default function Dashboard() {
	return (
		<div className="p-6 space-y-6">
			<Title level={3} className="!m-0">
				Dashboard
			</Title>

			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				{layers.map((layer) => (
					<Card
						key={layer.key}
						className="rounded-xl"
						styles={{ body: { padding: 24 } }}
					>
						<div className="flex items-center gap-3 mb-4">
							<div
								className="w-10 h-10 rounded-lg flex items-center justify-center"
								style={{ background: layer.color + "1a", color: layer.color }}
							>
								{layer.icon}
							</div>
							<Link to={`/live/${layer.key}`}>
								<Title level={4} className="!mb-0" style={{ color: layer.color }}>
									{layer.label}
								</Title>
							</Link>
						</div>
						<Text type="secondary" className="text-sm">
							{layer.description}
						</Text>

						<div className="mt-6 pt-4 border-t border-gray-100">
							<Text type="secondary" className="text-xs">
								— placeholder —
							</Text>
						</div>
					</Card>
				))}
			</div>
		</div>
	);
}
