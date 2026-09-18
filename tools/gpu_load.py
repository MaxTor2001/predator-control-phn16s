"""Нагрузить дискретную видеокарту вычислительным шейдером на N секунд, печатая скорость каждые 10 с.

Запуск: uv run --no-project --with wgpu tools/gpu_load.py 60 [heavy]
light (по умолчанию) - чистая арифметика, ~65 Вт; heavy - со случайными чтениями из памяти, упирается в лимит мощности.
Первые ~20 с драйвер держит GPU в P4 (~19 Вт), сравнивать нужно интервалы после выхода в P0.
"""

import sys
import time

import wgpu

SHADER = """
@group(0) @binding(0) var<storage, read_write> data: array<f32>;

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let i = id.y * 16776960u + id.x;
    let n = arrayLength(&data);
    if (i >= n) { return; }
    var x = data[i];
    var j = i;
    for (var k = 0u; k < STEPS; k = k + 1u) { BODY }
    data[i] = x;
}
"""
LOADS = {
    "light": (4_000_000, "20000u", "x = sin(x) * 1.0001 + cos(x * 0.5);"),
    "heavy": (
        32_000_000,
        "150u",
        "j = (j * 1664525u + 1013904223u) % n; x = sin(x + data[j]) * 1.0001 + cos(x * 0.5);",
    ),
}

seconds = int(sys.argv[1])
COUNT, steps, body = LOADS[sys.argv[2] if len(sys.argv) > 2 else "light"]
SHADER = SHADER.replace("STEPS", steps).replace("BODY", body)
adapter = next(
    a
    for a in wgpu.gpu.enumerate_adapters_sync()
    if a.info["adapter_type"] == "DiscreteGPU" and a.info["backend_type"] == "Vulkan"
)
device = adapter.request_device_sync()
buffer = device.create_buffer(size=COUNT * 4, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)
pipeline = device.create_compute_pipeline(
    layout="auto", compute={"module": device.create_shader_module(code=SHADER), "entry_point": "main"}
)
bind_group = device.create_bind_group(
    layout=pipeline.get_bind_group_layout(0), entries=[{"binding": 0, "resource": {"buffer": buffer}}]
)

passes = marked = 0
start = mark = time.monotonic()
while time.monotonic() - start < seconds:
    encoder = device.create_command_encoder()
    compute = encoder.begin_compute_pass()
    compute.set_pipeline(pipeline)
    compute.set_bind_group(0, bind_group)
    compute.dispatch_workgroups(min(COUNT // 256 + 1, 65535), COUNT // 16776960 + 1)
    compute.end()
    device.queue.submit([encoder.finish()])
    device.queue.read_buffer(buffer, 0, 4)  # дождаться завершения прохода
    passes += 1
    now = time.monotonic()
    if now - mark >= 10:
        print(f"t={now - start:.0f}с: {(passes - marked) / (now - mark):.2f} проходов/с", flush=True)
        mark, marked = now, passes
