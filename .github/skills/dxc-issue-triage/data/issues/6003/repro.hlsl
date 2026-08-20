[[vk::binding(0)]] Texture2D texture_;
[[vk::binding(0)]] SamplerState sampler_;

[shader("raygeneration")]
void main() {
    texture_.SampleLevel(sampler_, float2(0.3f, 0.4f), 0);
}