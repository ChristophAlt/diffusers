# coding=utf-8
# Copyright 2022 The HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Conversion script for the LDM checkpoints. """

import argparse
import os
import torch
from diffusers import UNet2DModel


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo_path",
        default=None,
        type=str,
        required=True,
        help="The config json file corresponding to the architecture.",
    )

    parser.add_argument(
        "--dump_path", default=None, type=str, required=True, help="Path to the output model."
    )

    args = parser.parse_args()

    config_parameters_to_change = {
        "image_size": "sample_size",
        "num_res_blocks": "layers_per_block",
        "block_channels": "block_out_channels",
        "downscale_freq_shift": "freq_shift",
        "resnet_num_groups": "num_groups_norm",
        "resnet_act_fn": "act_fn",
        "resnet_eps": "norm_eps",
        "num_head_channels": "attention_head_dim",
    }

    key_parameters_to_change = {
        "time_steps": "time_proj",
        "mid": "mid_block",
        "downsample_blocks": "down_blocks",
        "upsample_blocks": "up_blocks",
    }

    model = UNet2DModel.from_config(args.repo_path)
    config = dict(model.config)

    for key, value in config_parameters_to_change.items():
        if key in config:
            if isinstance(value, dict):
                new_list = []

                for block_name in config[key]:
                    # map old block name to new one
                    new_list.append(value[block_name])
            else:
                config[key] = value

    config["down_blocks"] = [k.replace("UNetRes", "") for k in config["down_blocks"]]
    config["up_blocks"] = [k.replace("UNetRes", "") for k in config["up_blocks"]]

    model = UNet2DModel(**config)

    state_dict = torch.load(os.path.join(args.repo_path, "diffusion_pytorch_model.bin"))

    new_state_dict = {}
    for key, new_key in key_parameters_to_change.items():
        for param_key, param_value in state_dict.items():
            if param_key.endswith(".op") or param_key.endswith(".Conv2d_0"):
                continue
            else:
                new_state_dict[param_key.replace(key, new_key) if param_key.startswith(key) else param_key] = param_value

    model.load_state_dict(state_dict)
    model.save_pretrained(args.repo_path + "_new")
