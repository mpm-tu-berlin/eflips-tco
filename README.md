# The TCO calculation software module

This software module was developed as an addition to the eFLIPS software series for a comprehensive total cost of 
ownership (TCO) analysis of the electric bus network simulated with [eflips-depot](https://github.com/mpm-tu-berlin/eflips-depot.git). 


<!-- GETTING STARTED -->
## Getting Started
<!--
### Prerequisites

Here, you should list what software is required to run the project. For example, you might need to install OpenLCA 
(which version?), whether it runs on Windows, Mac, or Linux or whether a specific Python version is required.

Basically, if it is something you cannot install with a simple `pip install`, you should list it here.
-->
### Installation

<!--_Below is an example of how you can instruct your audience on installing and setting up your app. This template doesn't rely on any external dependencies or services._
-->
1. Clone this git repository
   ```sh
   git clone https://github.com/mpm-tu-berlin/TCO-calculation.git
   ```
2. Install the packages listed in ```poetry.lock``` and ```pyproject.toml``` using the following command:
   ```sh
    poetry install 
   ```
### Database
After simulating a scenario in [eflips-depo](https://github.com/mpm-tu-berlin/eflips-depot.git), you need to connect 
the obtained database to this project within your IDE. The environmental variable `DATABASE_URL` needs to be set to the 
URL of your database.

<!-- USAGE EXAMPLES -->
## Usage

This software module allows you to calculate the TCO of a simulated bus network.

### Folder Structure

#### `src/`
The source code of the TCO-calculation software is stored here. Additionally, there are important files required for the 
TCO calculation.

##### `input_tco.json`

This file includes all input data required for the TCO calculation. Please edit the input parameters to meet your 
specifications.

#### `pyproject.toml`
This file includes the dependencies and information about the project.

#### `poetry.lock`
This file includes the information for poetry to install the dependencies.

<!--#### `LICENSE.md`
This file contains the license for the project. You should choose a license that fits your needs. [Choose an Open Source License](https://choosealicense.com)
-->
#### `README.md`
This file contains the information about the project.

### Analysis

#### Bar charts of efficiency and specific TCO

For the graphical presentation of your results, you need to save the result file produced by the `tco_calculation(...)` 
callable by setting the variable `save_result` to `True`. After calculating different scenarios, please specify the 
`scenario_id` of each of the scenarios, which should be included in the analysis and for which there is a `result_scn_ID.json`
in the directory, in the callables at the end of the main.

#### Sensitivity analysis

To conduct the sensitivity analysis for a specific scenario, you need to add the names of the desired parameters to the 
`parameter_list` of the callable `sensitivity_analysis(...)`. The names of the parameters must be identical with the 
ones given in the `capex_input_dict`, the `opex_input_dict` and the `general_input_dict`. Possible input parameters 
could be: `["procurement", "useful_life", "staff_cost", "maint_cost_vehicles", "maint_cost_infra", "fuel_cost",
 "interest_rate", "discount_rate"]`.
<!-- DOCUMENTATION -->
<!--## Documentation

This project is documented using the [Sphinx](https://www.sphinx-doc.org/en/master/) documentation generator. The documentation is in the `docs` directory. Sphix-Autoapi is used to automatically generate documentation from the source code's docstrings. To build the documentation, run the following command:

```sh
source venv/bin/activate
cd docs
sphinx-build -b html . _build
```

The documentation will be built in the `_build` directory. Open the `index.html` file in your browser to view the documentation.
-->
<!-- ROADMAP -->
<!--## Roadmap

- [x] Add Changelog
- [x] Add back to top links
- [ ] Add Additional Templates w/ Examples
- [ ] Multi-language Support
    - [ ] Chinese
    - [ ] Spanish-->
<!-- See the [open issues](https://github.com/othneildrew/Best-README-Template/issues) for a full list of proposed features (and known issues).-->
<!--
<p align="right">(<a href="#readme-top">back to top</a>)</p>
-->
<!-- CONTRIBUTING -->
<!--## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>
-->
<!-- LICENSE -->
<!--## License

Distributed under the WTFPL License. See `LICENSE.txt` for more information. **For your project, you should choose a license that fits your needs. [Choose an Open Source License](https://choosealicense.com)**
-->
<!-- CONTACT -->
## Contact

j.dubiel@campus.tu-berlin.de

Project Link: [https://github.com/mpm-tu-berlin/TCO-Calculation](https://github.com/mpm-tu-berlin/TCO-Calculation)

<!-- ACKNOWLEDGMENTS -->
<!--## Acknowledgments

Use this space to list resources you find helpful and would like to give credit to. -->