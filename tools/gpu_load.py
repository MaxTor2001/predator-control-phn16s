"""Нагрузить дискретную видеокарту вычислительным шейдером на N секунд, печатая скорость каждые 10 с.

Запуск: uv run --no-project --with wgpu tools/gpu_load.py 60
Первые ~20 с драйвер держит GPU в P4 (~19 Вт), сравнивать нужно интервалы после выхода в P0.
"""

import sys
import time

import wgpu

SHADER = """
@group(0) @binding(0) var<storage, read_write> data: array<f32>;

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    if (id.x >= arrayLength(&data)) { return; }
    var x = data[id.x];
    for (var k = 0u; k < 20000u; k = k + 1u) { x = sin(x) * 1.0001 + cos(x * 0.5); }
    data[id.x] = x;
}
"""
COUNT = 4_000_000

seconds = int(sys.argv[1])
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
    compute.dispatch_workgroups(COUNT // 256 + 1)
    compute.end()
    device.queue.submit([encoder.finish()])
    device.queue.read_buffer(buffer, 0, 4)  # дождаться завершения прохода
    passes += 1
    now = time.monotonic()
    if now - mark >= 10:
        print(f"t={now - start:.0f}с: {(passes - marked) / (now - mark):.2f} проходов/с", flush=True)
        mark, marked = now, passes
