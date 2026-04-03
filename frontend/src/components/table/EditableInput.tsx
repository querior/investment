import { EditOutlined } from "@ant-design/icons";
import { Button } from "antd";
import { useRef, useState } from "react";

const EditableInput = ({
	value,
	onSave,
}: {
	value: string | null;
	onSave: (v: string) => void;
}) => {
	const [editing, setEditing] = useState(false);
	const [val, setVal] = useState(value ?? "");
	const inputRef = useRef<HTMLInputElement>(null);

	const startEdit = (e: React.MouseEvent) => {
		e.stopPropagation();
		setVal(value ?? "");
		setEditing(true);
		setTimeout(() => inputRef.current?.focus(), 0);
	};

	const commit = () => {
		setEditing(false);
		onSave(val);
	};

	if (editing) {
		return (
			<input
				ref={inputRef}
				value={val}
				onChange={(e) => setVal(e.target.value)}
				onBlur={commit}
				onKeyDown={(e) => {
					if (e.key === "Enter") commit();
					if (e.key === "Escape") setEditing(false);
				}}
				onClick={(e) => e.stopPropagation()}
				className="border border-blue-400 rounded px-1 text-sm w-full outline-none"
			/>
		);
	}

	return (
		<div className="flex items-center justify-between gap-2 min-w-0">
			<span className="truncate text-sm">
				{value ?? <span className="text-gray-400">—</span>}
			</span>
			<Button
				type="text"
				size="small"
				icon={<EditOutlined />}
				onClick={startEdit}
				className="shrink-0"
			/>
		</div>
	);
};

export default EditableInput;
