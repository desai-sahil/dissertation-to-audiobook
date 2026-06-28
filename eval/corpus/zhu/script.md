An audiobook rendering of In-plant applications of a micro-tensiometer water stress sensor.

<break time="0.8s"/>

IN-PLANT APPLICATIONS OF A MICRO-TENSIOMETER WATER STRESS SENSOR.

<break time="0.8s"/>

A Thesis.

<break time="0.8s"/>

Presented to the Faculty of the Graduate School of Cornell University in Partial Fulfillment of the Requirements for the Degree of Master of Science by Siyu Zhu January two thousand seventeen

ABSTRACT.

<break time="0.8s"/>

Climate change has caused extreme weather conditions, and resulted in a large water stress in agriculture. Monitoring plant water stress is crucial for both the study of on plant drought responses and the improvement of the agricultural water use efficiency. However, current commercially available water stress sensors either lack accuracy and resolution, or are too complicated to use. In this study, we developed a micro-tensiometer (micro T M), which measures plant water stress in real time by monitoring the stem water potential and the soil water potential - the two most important plant water stress indicators — with high accuracy, high resolution, minimum sample destruction, and optimum local geometrical integration with the sample.

The mu TM translates the water energy state into electronic signal by implementing traditional tensiometry in a microelectromechanical system (microelectromechanical systems (M E M S)) with the nanoporous silicon membrane (P o S i) technique. This design significantly increased the measurement range from greater than - zero point one megapascals to greater than minus ten megapascals. With the M E M S approach, the sensing area was reduced by two orders of magnitude (from greater than ten square centimeters to zero point two five square centimeters).

In situ embedding strategies were developed for the micro T M through testing on apple trees. In an in-plant experiment (greenhouse experiment two (G H two)), the micro T M (approximately minus two point five megapascals) showed up to one point five megapascals difference from the traditional Scholander pressure chamber (approximately minus one point zero megapascals). This result led to the hypothesis that a vapor gap existed between the micro T M and the tissue, and could result in a seven point seven seven megapascals per degree Celsius error of temperature difference between the sample and sensor at twenty-five degrees C. Different strategies were tried to reduce the vapor gap in the fourth experiment (greenhouse experiment four (G H four)). The micro T M with the best contact showed a linear correlation ( R-squared equals zero point nine three) with the Scholander. Other discoveries from the G H four, and their related hypotheses were discussed as well.

BIOGRAPHICAL SKETCH.

<break time="0.8s"/>

Siyu began her undergraduate education in two thousand eleven in Chemical Engineering at the University of Minnesota-Twin Cities. In Minnesota, Siyu studied under Dr. Wei-Shou Hu for his project on the mechanisms that inhibit the transfer of antibiotic resistance among bacteria cells. After receiving her degree in two thousand fourteen, Siyu continued her research career in Cornell University under the supervision of Drs. Abraham Duncan Stroock (Chemical Engineering, Ithaca), Donald Koch (Chemical Engineering, Ithaca), and Lailiang Cheng (Horticulture, Ithaca), on the work presented in this thesis.

ACKNOWLEDGEMENTS.

<break time="0.8s"/>

I would like to thank my advisor, Dr. Abraham Stroock, who has been an excellent mentor and helped me develop into a better researcher. I would also like to thank my committee members, Drs. Lailiang Cheng and Donald Koch, who have provided invaluable assistance with my research. I extend my gratitude to my collaborators, Drs Alan Lakso and Taryn Bauerle, who have given me valuable suggestions for my research.

I am also grateful to my research colleagues, Michael Santiago, Winston Black, Annika Kreye, Olivier Vincent, Hanwen Lu, I-Tzu Chen, and Erik Huber, who have worked with me every day and provided constant help throughout the course of my research. Finally, I would like to thank my family and friends for their unconditional support throughout my life.

LIST OF FIGURES.

<break time="0.8s"/>

Table one. This table lists the figures included in a thesis about measuring plant water stress, covering topics from the importance of water in agriculture to the working principles and experimental results of a micro-tensiometer used to monitor stem water potential in plants.

Table two. The thesis contains figures showing the micro-tensiometer in soil and the orchard and growth chamber experiment setup plan, located on pages sixty-five and sixty-eight respectively.

TABLE OF CONTENTS.

<break time="0.8s"/>

Table three. This table presents the table of contents of a scientific thesis investigating plant water potential measurement, covering background on vapor-liquid equilibrium and water movement through the soil-plant-atmosphere continuum, the development and calibration of micro-tensiometer sensors using nanoporous silicon membranes, greenhouse experiments, and results discussing water potential gradients in plant stems.

Table four. This table shows the final sections of a thesis, including the conclusion, references, and appendices containing technical materials such as fabrication masks, data logging programs, data analysis code, and a two-dimensional heat transfer simulation program, with their corresponding page numbers.

less than span id equals "page-nine to zero" greater than I. INTRODUCTION.

<break time="0.8s"/>

Climate change has resulted in global temperature rising, carbon dioxide concentration elevation, and increasing variability in precipitation. Warmer temperature increased the water withdrawal from the earth through evapotranspiration, and reduced the water supply recharge at the same time. Therefore, water supply sustainability is at risk \(Figure I-one a (#page-eleven to zero)). Water is important for agriculture. Irrigated agriculture occupies up to eighty to ninety percent of total water consumption of the U.S. The extremes in temperature and the frequency in precipitation challenge the adaptability of crops to water stress, and have stimulated studies to quantify crop stress responses. To increase the water use efficiency (W U E), which measures the grain yield per unit amount of water supplied, studies have been done to understand the water stress responses of plants and to develop gene modified crops with drought tolerance. Nevertheless, most of the plant drought response processes are understood incompletely, due in part to the lack of a tool that can monitor plant water stress accurately in real time, and with minimal destruction of the plant. Additionally, a recent study has shown that destructive sampling methods disturb the original water stress status inside the sample, and result in unreliable measurements. The original model of water transport in plants as a soil-plant-atmosphere continuum (S P A C) has been proposed in one thousand nine hundred forty-eight by Van den Honert, but few direct measurements have been done to prove its reliability. Furthermore, scientists have been trying to understand the water stress distribution inside plants, more specifically, the radial distribution of water stress in plants. Without an appropriate tool, they have to combine the radial sap flow data in trees with laboratory measured hydraulic resistance of cut wood, to predict the water stress radial distribution. Moreover, the mechanism of the plant regulation of stomata conductance, which is a crucial topic when it comes to plant drought responses, has been debated for decades. The stomatal conductance regulates the rate of transpiration and photosynthesis, and therefore, directly affects the vegetative growth and reproduction of plants. Without a reliable tool that can measure the soil and plant water stress in situ with high-resolution and fast response, after sixty years of debate, scientists still hold different opinions about whether the soil water stress induced chemical signaling, or the leaf water stress is the key parameter for stomatal regulation. In summary, the lack of an in-situ tool with high-resolution, high-accuracy, fast response, and minimal plant destruction has been holding back the study on plant water stress for decades.

In this study, we developed a new water stress sensor called a micro-tensiometer, and tested its applications in living trees in a greenhouse. Preliminary testing showed a linear correlation between the sensor and the Scholander Pressure Chamber, the widely accepted water stress measuring equipment, on living apple trees. The working mechanism of this sensor is based on the metastable vapor liquid equilibrium (M V L E). To develop this sensor, we coupled the idea of a traditional tensiometer with the M E M S technology, and built a micro-scale water stress sensor with a two orders of magnitude larger measurement range by adopting the nanoscale porous silicon membrane technique developed by the Stroock Group. With the ability to measure high resolution and high accuracy real time water stress, we aim to use this sensor to address unanswered plant physiological questions mentioned above, to screen plants with new drought tolerance genotypes, and to discover new phenomenon that cannot be observed in the past \(Figure I-one b (#page-eleven to zero)). In agriculture, the sensor can be integrated with a sophisticated water stress monitoring feedback loop computer system that controls when and how much to irrigate \(Figure (#page-eleven to zero) I-one c (#page-eleven to zero)). Moreover, this tool can be applied to conduct further studies on metastable liquids and ecophysiological studies.

less than span id equals "page-eleven to zero" greater than Figure I-one Importance of Water on Agriculture - (a) Water Supply Sustainability is at Risk. two - (b) Expected Application of the Water Stress Sensor for Plant Drought Response Studies by monitoring the plant water stress at five different locations on one tree: soil, root, stem, branch and leaf. - (c) Expected Application of Water Stress Sensor for Irrigation Scheduling. The sensor can be integrated into an irrigation feedback loop. The correlation between the crop productivity and the water stress level could be studied as a reference for accurate water level control. The computer monitored precise irrigation could be realized. sixty-one

less than span id equals "page-twelve to zero" greater than II. BACKGROUND.

<break time="0.8s"/>

less than span id equals "page-twelve to one" greater than Metastable-Vapor-Liquid-Equilibrium (M V L E).

<break time="0.8s"/>

All liquids can sustain reduced pressure or even some tension due to their molecular interactions. This phenomenon is called cohesion. Water is more stable under tension than most liquids due to the strong hydrogen bonding between water molecules \(Figure II-one a (#page-fourteen to zero)). At this condition, liquid water is in a superheated metastable phase. Cavitation occurs when the tension reaches the stability limit of liquid water, and is able to create a vapor bubble nucleation. After cavitation, the liquid and vapor phase of water will reach a saturated liquid-vapor phase equilibrium.

There are a variety of methods to stretch liquid water and make it metastable. In tensiometry, tension occurs due to metastable-vapor-liquid-equilibrium (M V L E), where a volume of liquid water is in metastable equilibrium with the outside sub-saturated vapor through a thin layer of nanoscale porous silicon. thirteen,fifteen As Figure II-one b (#page-fourteen to zero)&c illustrate, when changing the vapor phase from saturated to sub-saturated state, water evaporates from the air-liquid interface inside the pores and forms a curved meniscus. The capillary pressure of the meniscus balances the pressure difference between the liquid and the outside environment. Based on Young-Laplace Equation (one), the capillary force is proportional to the surface tension () and the cosine of the contact angle () between the silicon and liquid water surface, and is inversely proportional to the radius of the pore size. By using nanoscale pores, we are able to generate a large tension inside the bulk liquid ( greater than or equal to negative twenty megapascals). thirteen

Equation one.

The liquid pressure in the metastable state can be derived by assuming isothermal conditions and at the condition for phase equilibrium: the chemical potential of liquid water (mu liquid) and vapor (chemical potential of water vapor (mu vapor)) are the same.

Equation two.

Where chemical potential of pure water at standard conditions (mu naught) is the chemical potential of pure liquid water and vapor at standard temperature (T) and pressure (P zero ).

Combining equation (three) and (four), the sub-saturated liquid pressure is expressed below:

Equation five.

In Eq. (five), we indicate that the pressure difference required by phase equilibrium must be equal to that due to capillarity.

Once the tension is large enough to reach delta equals delta receding, the contact angle reaches the receding contact angle () between silicon and water. Once the tension is larger than the maximum capillary pressure, the meniscus will no longer hold, and the air-liquid interface will recede into the bulk liquid. This mechanism of cavitation is called air-invasion.

The application of M V L E in the micro-tensiometer will be discussed in Section II.D (#page-twenty-seven to zero) in detail.

less than span id equals "page-fourteen to zero" greater than Figure II-one Water under Metastable State (a) The schematic representation of the P-T phase diagram of water. Water can be stretched from pure saturated liquid water to metastable liquid water by isothermally pulling on the water along the blue arrow. The liquid water can stay in a metastable state at negative pressure due to the strong attractive interactions between liquid water molecules.

(b) A schematic diagram of M V L E in true equilibrium. Liquid water is connected to the outside vapor through a porous membrane with an average pore diameter of. At saturated state, the hydrostatic pressure of liquid water equals atmospheric pressure, and the vapor is in saturated vapor state. The liquid and vapor are at equilibrium.

(c) A schematic diagram of M V L E in metastable equilibrium. The same vapor-membrane-liquid system under sub-saturated state. The vapor pressure is lower than the saturated vapor pressure. The water evaporates from liquid state to vapor state until a stable curved meniscus forms. The surface tension of the meniscus pulls liquid water inside the reservoir and caused a lowered hydrostatic pressure that equals the capillary pressure.

less than span id equals "page-fifteen to zero" greater than Soil-Plant-Atmosphere Continuum (S P A C).

<break time="0.8s"/>

Water is important for plants and soils to maintain hydration, and as a reagent in the photosynthetic reaction and as a nutrient transporter. The soil-plant-atmosphere continuum describes the water movement from the soil, through the plant, to the atmosphere. This movement is driven by the gradient in the energy state of water from high to low. The soil is the source of water for the continuum, and has higher chemical potential. The atmosphere is the sink of the water flow, and has the lower chemical potential. Water evaporates from the leaves to the atmosphere through transpiration. The transpiration creates a negative pressure on the water inside the plant and pulls water from the soil to the atmosphere \(Figure II-two\) (#page-eighteen to zero). The S P A C can be treated as a M V L E system with soil as a large reservoir of liquid water, plant as the porous membrane, and the atmosphere as the sub-saturated vapor.

less than span id equals "page-fifteen to one" greater than II.B.one. Energy State of Water.

<break time="0.8s"/>

Water potential () is commonly used in plant science to describe the energy state of water. It is defined as the chemical potential of water () relative to pure water ( zero) divided by the molar volume of pure water () at that temperature and pressure:

Equation six.

Therefore, water potential is the chemical potential of water in pressure units. It represents the free energy of water per unit volume relative to pure water. Water movement in S P A C happens spontaneously along a gradient in water potential.

Based on Eqn. (three), the vapor water potential can be expressed as

Equation seven.

Similarly, the liquid water potential can be expressed as

Equation eight.

At equilibrium (true or metastable), the liquid water potential equals the vapor water potential. This liquid-vapor relationship is the well-known Kelvin equation, as shown below:

Equation nine.

Water potential has been an important indicator for both plant and soil drought status. For example, soil water potential has been used to schedule irrigation for agriculture. Plant scientists divided water potential into four terms based on its four major contributors. The four major components are osmotic potential (), pressure potential (), matric potential (), and gravity potential ():

Equation ten.

The osmotic potential is the reduction of the water potential due to the dissolved solutes, such as sugars and mineral nutrients. Pressure potential represents the hydrostatic pressure of water. It can be positive, as turgor pressure in cells, or negative, as water under tension in xylem (see Section II.B.three (#page-twenty-one to zero) for details). Matric potential represents the capillary and adsorption effect from solid phases, such as soil particles and mesophyll cells in leaves \(Figure II-two (#page-eighteen to zero) b&d). Water adsorbs onto the wettable surface of the solid particles, and forms menisci in the small pores between them through capillarity. These menisci generate negative pressure due to surface tension, as explained in Section II.A (#page-twelve to one) Eqn. (one). The smaller the radius of curvature of the meniscus, the more negative the matric potential will be. The plant tissue can also be treated as a polymer gel. Based on Flory-Huggins theory, the matric potential of a wet tissue can be treated approximately as the osmotic potential of a solid polymer solution. twenty Hence, the matric potential of a sample depends on the inherent surface characteristics of a sample, its moisture fraction, particle size, and particle distribution. We use water content to describe the moisture fraction of a material. It is defined as the volumetric fraction of water in a wet matrix, equals V-water over V-water plus V-dry, where is the volume of water in the matrix, and is the volume of the dry matrix. Every material has a typical water retention curve theta ( psi, T), which shows the relationship between the water potential and the water content. Some hygrometers measure water potential by measuring the water content of a material (e.g. concrete) with a calibrated water retention curve. The last potential component is gravity potential, equals minus ℎ, where equals nine hundred ninety-seven kilograms per cubic meter is liquid water density; equals nine point eight one meters per second squared is the gravitational constant; ℎ is the height relative to the reference state. Gravity potential pulls water towards soil through gravitational force, and reduces plant water potential to a more negative value. Its value depends on the reference level, and plays a key role in soil drainage.

less than span id equals "page-seventeen to zero" greater than II.B.two. Water Movement Through S P A C.

<break time="0.8s"/>

Soil is the water source for the S P A C. Different soil types have different water holding capacity. This capacity depends on the matric characteristics discussed in the previous section. For example, clay has higher water holding capacity than sand because clay has smaller particles, under two micrometers, less than one millimeter,. Smaller particle size means larger surface area for water adsorption per unit volume, and smaller pores between particles for meniscus formation. The small pores trap water through capillarity and prevents water from drainage due to gravity. As shown in Figure II-two- (#page-eighteen to zero)d, at high water potential, both clay and sand have high water content. However, for a water potential decrease from minus one thousand to minus one hectopascals, sand has a sharp reduction in water content, while clay has moderate decrease in water content. Therefore, clay has the highest water holding capacity than the other two soil types, and sand has the lowest water holding capacity. Water moves from more saturated soil to less saturated soil, for example, around the roots, down the gradient of water potential. eighteen

less than span id equals "page-eighteen to zero" greater than Figure II-two Water Movement through a Plant.

- (a) A schematic diagram of transpiration. Water potential gradient in the direction from soil to the atmosphere drives the transpiration. - (b) A diagram of the site of evaporation in leaf. Water evaporates from the water covered sites in the leaves to the atmosphere through stomata. - (c) A diagram of water transport in stem xylem elements. Water can bypass the cavitated elements through pit membranes. The nano-scale pores on porous pit membrane prevented air invasion from cavitated xylem elements to functioning xylem elements through capillarity. - (d) A diagram of water adsorption onto soil particles. The plot on the right shows the water retention curve of different soil types (reproduced from Buckingham one thousand nine hundred seven sixty-two). (Figures Modified from Stroock two thousand fourteen twenty-four) At the site of the root-soil interface, the ability of roots to absorb water depends on the water potential difference across the root cell membrane. This driving force is mainly contributed by pressure potential and osmotic potential. As soil dries out, the water uptake from the soil to the root will cease, due to the large hydraulic resistance between the soil and the root when the soil and root water potential are lowered to a critical value.

The water movement mechanism in stems from root to leaf was first proposed as Cohesion-Adhesion theory by Dixon and Joly in one thousand eight hundred ninety-four. Due to the strong molecular interaction between liquid water molecules, water is able to remain in liquid phase under negative pressure. Due to the strong intermolecular interactions between the water molecules and the hydrophilic surface of the xylem wall, which is called adhesion, water can be pulled from the root to the leaf through capillarity under negative pressure. This negative pressure is created at the evaporation site from leaves, through liquid-vapor equilibrium and capillarity as described by the Kelvin-Laplace equation (Eqn. (five) in Section II.B.one\) (#page-fifteen to one). Water transport in the stem happens mainly through the xylem \(Figure II-two- (#page-eighteen to zero)c). Xylem conduits are composed of small xylem elements interconnected with each other through pit membranes. These xylem elements are elongated, hollow, dead cells with thick highly lignified secondary walls. They form longitudinal stacks to effectively transport water. Compared to living cells with their intact plasma membrane, xylem allows water to be transported from root to leaf with minimum hydraulic resistance. The walls of xylem conduits prevent them from collapsing when the water in the xylem is experiencing large tension (~ minus ten megapascals). The pit membranes originated from primary walls of the dead cells. They are nano-scale to micro-scale porous membranes composed of cellulose microfibrillar matrix. Cavitation happens when the tension is larger than the stability limit of the water in a xylem element, or when there is air-invasion from a neighboring non-functioning gas-filled xylem elements. If one xylem element cavitates due to the negative pressure or air-seeding, the airwater interface will be trapped inside the pores of the pit membranes. This capillary force prevents air from entering the neighboring functioning xylem elements. Water can still bypass the cavitated xylem elements by going through the surrounding non-cavitated xylem elements through the pit membrane \(Figure II-two- (#page-eighteen to zero)b). Although pit membranes increase the resistance of water transport in xylem, they also protect against the spreading of the cavitated (embolized) zone from spreading.

The evaporation sites in the leaves could be the mesophyll cell walls, the leaf xylem conduits, or the tissue around the stomata. We could assume these wetted surfaces are hydrophilic porous matrices. The menisci formed in these wettable porous membranes create a large tension and pull water from the root to the leaf.

Evaporation from a leaf's interior is significantly inhibited by the cuticle. twenty-six Water can mostly diffuse to the atmosphere through stomata. Stomata are pores on the epidermis of leaves, and regulate the gas exchange between inside the plant and the atmosphere. Stomata open during the day in response to sunlight to start the photosynthesis. Photosynthesis produces the carbohydrates for the growth and reproduction of the plants. Stomata opening allows carbon dioxide, the carbon source of photosynthesis, to enter the plant, the oxygen produced by photosynthesis to be released into the environment, and the water vapor to diffuse out of plants. The evaporation is driven by the vapor pressure deficit ( equals one hundred minus percent relative humidity). For one carbon dioxide to enter stomata, approximately four hundred water molecules are lost to the atmosphere. This gas exchange ratio shows that plants need to transpire a lot of water to sustain the normal operation of photosynthesis. Under severe water stress, plants close their stomata through physiological regulation, and slow down the rate of transpiration. The water stress affects the rate of photosynthesis at the same time. twenty-eight

less than span id equals "page-twenty-one to zero" greater than II.B.three. Soil-Root-Leaf Water Relations.

<break time="0.8s"/>

The diurnal variations of soil-plant water relations are shown in Figure II-three. (#page-twenty-one to one) Figure II-three- (#page-twenty-one to one)a is a hypothetical sketch based on the theory. Figure II-three- (#page-twenty-one to one)b is an unusual set of experimental data that coincided the theoretical hypothesis; reproduction of results such as these has been hindered by the lack of appropriate tools. The rate of transpiration is not only related to plant and soil responses, but is also influenced by V P D and solar intensity. The solar energy heats up the leaves and drives their water evaporation. V P D drives the diffusion of water vapor from inside the leaves to the outside environment, as explained in the previous section. During the day, the solar

less than span id equals "page-twenty-one to one" greater than Figure II-three Soil-Root-Leaf Water Relations - (a) Hypothetical Sketch for the Diurnal Variations of Soil-Plant Water Relations. sixteen Solid bars indicate twelve-hour dark periods. During the day, the leaf water potential decreases to a more negative value than the root water potential due to transpiration. The dashed line at minus one point five megapascals represents the wilting point of the plant. As the soil gets drier, the soil water potential decreases (to more negative values), the predawn plant water potential (leaf and root) always returns to the soil water potential, until the wilting point is reached. - (b) Experimental Results for the Diurnal Variations of Soil-Plant Water Relations. sixty-three (Note that the y-axis is in negative bars) The diurnal variations of a pepper leaf water potential was compared with the soil water potential around the root. The leaf water potential was obtained by measuring the water content of a leaf through beta -ray transmission. The leaf water potential can be found through a known water retention curve. The soil water potential was measured through a traditional tensiometer. At the beginning, the predawn leaf water potential does not return to the soil water potential. As the soil gets drier, the predawn leaf water potential reached soil water potential until the wilting point.

intensity regulates the opening of stomata to start the gas exchange of water and carbon dioxide between the plant and the atmosphere. Water evaporation from the leaf generates a gradient of water potential from the root (less negative water potential) to the leaf (more negative water potential) in the plant \(Figure II-three- (#page-twenty-one to one)a). The maximum water potential measured during the day is the midday water potential (). At night, no sun light is sensed by the leaves, so the stomata are closed, which means the transpiration and photosynthesis are stopped. The plant water potential progressively relax (less negative) to the same level as the soil water potential. The least negative diurnal leaf water potential is called the predawn water potential ().

less than span id equals "page-twenty-two to zero" greater than II.B.four. Stem Water Potential indicates Plant Stress Level..

<break time="0.8s"/>

Both leaf water potential and stem water potential are good indicators for plant water stress level. The predawn leaf water potential indicates the effective soil water potential, which integrates the complete root-soil system. However, during the day, the leaf water potential is easily affected by the variations of the transpiration rate, and shows large variations in measurements. Furthermore, single leaf water potential measurements cannot represent the stress level of the entire tree, because different leaves experience different micro-environments. This micro-environment is affected by the shading from other leaves, wind speed around the leaves, and physiological effects from nearby organs. Different from the leaf water potential, stem water potential integrates the effects from all the leaves and organs on a tree, and is the best plant water stress indicator, as recommended by Naor two thousand point two nine The stem water potential is closely correlated with the vegetative growth and the reproduction of plants \(Figure II-four\) (#page-twenty-three to one). The vegetative growth rate and the fruit growth rate decrease with the decreasing stem water potential, that is, more negative,.

less than span id equals "page-twenty-three to one" greater than Figure II-four Stem Water Potential is Important for the Reproduction and Vegetative Growth of Plants (a) The vegetative growth of an apple shoot under stress conditions and controlled well-watered conditions is compared in this plot. As stem water potential becomes more negative, the shoot growth rate is reduced. (b) The fruit growth rate of apple under stress and well-watered conditions (control) are compared. Similar to the shoot growth, when stressed, the fruit growth rate decreases with increasing stem water potential.

Therefore, monitoring the stem water potential is crucial for both plant physiology studies and for agriculture.

less than span id equals "page-twenty-three to zero" greater than Commercially Available Water Potential Sensors.

<break time="0.8s"/>

Water potential in plants and soils has a general range from zero to minus three megapascals, with a high requirement of near-saturation accuracy because most irrigated soils have a water potential range of zero to - zero point one five megapascals. The stem and leaf water potential are typically greater than minus ten megapascals. twelve,thirty-one There are four major types of commercially available hydrometers: the leaf Scholander pressure chamber, the thermocouple psychrometer, the electro-magnetic based sensors, and the tensiometer. Their accuracy, measurement range, response time, form factor, and ease of operation have been compared in Table II-one. (#page-twenty-four to zero) twenty-four The leaf Scholander pressure chamber is the most widely used ex situ hydrometer. It measures the leaf water potential by cutting the leaf off from the tree, sealing the entire leaf inside the pressure chamber with the cut end of the stem protruding out of the chamber, and slowly pressurizing the leaf with gas until water starts to come out from the cut end. The gas pressure inside the chamber at this point is equal and opposite to the leaf water potential. The water potential measured through this method are mainly pressure potential and osmotic potential of the leaf. This method is easy to operate, but requires labor to do measurements manually. Random error happens due to individual operation and subjective end point judgement. In addition, the high pressure gas used by the pressure chamber is hazardous. The thick-wall of pressure chamber is usually cumbersome.

The thermocouple psychrometer is the most accurate in situ plant hygrometer. It uses the dry bulb and wet bulb temperature difference to measure the relative vapor pressure the gas in Table II-one Commercially Available Hygrometers less than span id equals "page-twenty-four to zero" greater than equilibrium with the sample. Different from the pressure chamber, psychrometers can operate automatically. Nevertheless, the operation of most psychrometers is an intrinsic non-equilibrium process. The thermocouple junction is cooled to allow vapor condensate on it for wet bulb dew point temperature measurement. The vapor condensation process is never in equilibrium due to the varying tissue temperature. This temperature gradient from the tissue to the condensation point is hard to interpret and could cause significant error in measurements. Besides, the calibration and insulation required for accurate measurements are complicated. Therefore, this equipment has only been used for research purposes.

Table five. This table compares in situ and ex situ methods for measuring plant water potential, summarizing each method's measurement range, accuracy, response time, physical size requirements, and key limitations, showing that in situ methods like psychrometry and tensiometry allow continuous non-destructive monitoring but have narrow ranges or temperature sensitivity, while ex situ methods like the pressure chamber and chilled mirror hygrometer can cover wider ranges but require destructive sampling.

The electro-magnetic based sensors are mostly used for in situ soil water potential measurements for the prediction of irrigation scheduling. They measure the water content related electric resistance, capacitance, or heat dissipation of the material with known water retention curve (). Currently, a Decagon matric potential sensor (M P S)minus six is the best of this class of sensor. It measures the change of the dielectric permittivity of a porous ceramic disk due to the change of water content in the disk. The disk water status changes and equilibrates with the moisture level of the surrounding soils. The electronic response of the disk needs to be calibrated against its water content before application. The water potential of the sample can then be found from the water retention curve of the ceramic disk. A comparison was done between the M P S-six and the sensor we developed. These sensors have short response time, small form factor, but low accuracy.

Chilled mirror hydrometers are accurate ex situ water potential sensors. They measure the water potential of a sample with a high accuracy of plus or minus zero point zero five megapascals from zero to minus five megapascals, and one percent from minus five megapascals to minus three hundred megapascals. thirty-six After a measurement starts, the mirror temperature is lowered through a thermoelectric cooler until water vapor starts to condense on the mirror. The condensation will be detected by the photo detector due to the change in the mirror reflectance. The platinum resistor thermocouple (platinum resistance thermometer (P R T)) on the mirror will record the dew point temperature, which can be translated into water activity. Despite its accuracy, this hygrometer cannot be used for in situ continuous measurements. For soil measurements, the destructive sampling will break the integrity of the soil sample. We have been using this method in laboratory to measure the water potential of osmotic solutions. We use the measured osmotic solution for micro-tensiometer calibration.

Tensiometers translate the chemical potential into measurable mechanical tension through the M V L E theory discussed in Section II.A. (#page-twelve to one) Conventional tensiometers are the most accurate in situ soil water potential sensors. The reduction in liquid pressure can be sensed through the mechanical deflection of the pressure transducer directly attached to the liquid. Commercially available tensiometers have a high accuracy of plus or minus five times ten to the negative fourth, but a short measurement range of zero to minus zero point zero eight five megapascals thirty-eight \(Table II-one\) (#page-twenty-four to zero). The small measurement range is due to the air invasion through the micropores of the ceramic membrane, and defects and impurities that facilitate nucleation in the macroscopic internal reservoir in which the liquid is held. The limited range only allows the sensor to measure well-watered soils for moisture sensitive crops, but not for drier environment. Its relatively large form factor also affects the integrity of the sample.

The high accuracy of tensiometers motivates researchers to extend the measurement range with different approaches. Peck and Rabbidge introduced an osmotic tensiometer in one thousand nine hundred sixty-six, and extended the operating range to minus one point five megapascals. They filled the tensiometers with PEG two thousand solution, and use the osmotic potential of the solution to shift the reference potential of the tensiometer to a more negative value. This method has been developed further to reach a limit of minus one point six megapascals. Another approach was to reduce the pore size of the ceramic membrane from microscale to nanoscale; this method extended the limit to minus one point five megapascals. The study from our group has shown that using the M V L E method to connect a small volume of liquid (about zero point one milliliters) to the outside sub-saturated vapor through nanoscale porous membrane can reach a liquid pressure of less than or equal to negative twenty megapascals. This discovery initiated the idea to build a micro-scale tensiometer. The M E M S approach significantly reduced the sensing area of the tensiometer. With the first generation micro-tensiometer, our group has successfully extended the measurement range to minus ten megapascals, and significantly reduced the sensing area from greater than ten square centimeters to one point two square centimeters. The second-generation micro-tensiometer discussed below has a further reduced form factor of zero point two five square centimeters.

less than span id equals "page-twenty-seven to zero" greater than Micro-Tensiometer (micro T M).

<break time="0.8s"/>

A micro-tensiometer combines the tensiometry, the piezo-resistive M E M S (microelectric-mechanical systems) pressure sensing technique, and the nanoporous silicon membrane (P o S i). The P o S i increased the capillary pressure the membrane can hold; the small internal volumes (ten nanoliters) lowers chance of impurities that can catalyze nucleation. In addition, the cleanroom based micro-fabrication process reduced the impurities inside the liquid reservoir, minimizing the possible vapor nucleation sites, and helped extending the measurement range of the sensor.

less than span id equals "page-twenty-eight to zero" greater than Figure II-five The Working Mechanism of the Micro-tensiometer (micro T M) (a) Top and bottom side of the micro-tensiometer. To get a functioning micro T M, the cavity needs to be filled with water using a high pressure (approximately three point four five megapascals) cylinder. The liquid inside the cavity connects to the outside through nano-porous silicon membrane. An expanded view of the nano-porous silicon membrane with synthetic xylem veins etched was also shown. The synthetic xylem shortens the response time of the sensor. The veins are designed as a balance of immediate response and minimization of the chance of airinvasion due to random defects in the silicon membrane. (b) An enlarged view of liquid water in a nanoscale pore connect to the outside through a curved meniscus. The tension held by the nano-scale pores is determined by the pore size and the contact angle between the liquid water and silicon. The liquid water in the cavity reached metastable equilibrium state with outside sub-saturated water vapor through the capillarity of the nano-scale porous silicon membrane. (c) The cross-sectional view of the cavity and the diaphragm on top of it. The reduced pressure is sensed through the deflection of the diaphragm. The response time constant represents the time the sensor takes to respond to a step change of the outside vapor water potential. (d) An enlarged view of the Wheatstone Bridge (B R) and a P R T. The mechanical deflection of the diaphragm is transduced into electronic signal through the piezoresistors in the Wheatstone Bridge. The red resistors on the blue cavity are piezoresistors. The electronic signals are transferred to the outside by wiring the six pads to the outside datalogging system. A P R T (platinum resistor thermocouple) is placed on top of the porous silicon membrane to measure the accurate sample temperature.

less than span id equals "page-twenty-nine to zero" greater than II.D.one. M E M S (Micro-Electric-Mechanical-Systems).

<break time="0.8s"/>

The micro-scale pressure sensing system of the micro-tensiometer is based on the welldeveloped piezo-resistive-M E M S-diaphragm pressure sensing technique. M E M S is a technology that builds micro-scale devices with a system of electrical and mechanical components. The M E M S devices are manufactured based on the micro-fabrication technologies. A piezo-resistive pressure sensor translates the mechanical stress to electrical signal through a diaphragm with piezoresistors attached. The mechanical stress on a diaphragm is measured through the resistance change of the resistors in response to the stress. The piezo-resistive technique has been developed for macro-scale pressure sensing since the nineteen fifties. Combined with M E M S technology, piezo-resistive pressures sensors can be manufactured and applied in micro-scale.

Figure II-five (#page-twenty-eight to zero) shows the working mechanism of the micro T M. Figure II-five- (#page-twenty-eight to zero)a is the most recent version of micro T M. The cavity in Figure II-five- (#page-twenty-eight to zero)a is first filled with water under high pressure. The internal water connects to the outside through the P o S i with nano-scale pores \(Figure II-five- (#page-twenty-eight to zero)b). When measuring the sample water potential, the internal liquid pressure is reduced. The reduced pressure is measured through diaphragm deflection \(Figure II-five- (#page-twenty-eight to zero)c). The deflection will be sensed through the electronics on top of the diaphragm \(Figure II-five- (#page-twenty-eight to zero)d). In a micro T M, four piezoresistors were integrated into a Wheatstone bridge (B R) to eliminate the offset and to minimize the temperature effects of the resistors. Two resistors are placed at the top and bottom of the diaphragm to sense the maximum compressive stress () of the diaphragm. Two resistors are placed at the center of the diaphragm to sense the maximum tensile stress due to the maximum deflection. The signal from piezoresistors are maximized by using heavily boron-doped polycrystalline silicon (six times ten to the nineteenth per cubic centimeter), and by using a high resistance of two thousand. forty-seven

less than span id equals "page-thirty to zero" greater than II.D.two. Nanoporous Silicon Membrane (P o S i).

<break time="0.8s"/>

The P o S i was etched through anodization: silicon is an anode in the electrochemical etching set-up, and is etched by running current through an electrolyte made of hydrofluoric acid, ethanol and water. The anodization usually has platinum as cathode. The etched pore size and structure depends on the crystal orientation of the silicon (one-one-one crystal orientation in this case), the doping type of the silicon wafer (p-type), silicon resistivity (one to ten ohm-centimeters), electrolyte concentration, current density, and etching duration. The details of anodization are presented in the Chapter III. (#page-thirty-nine to zero)

less than span id equals "page-thirty to one" greater than II.D.three. Sensitivity.

<break time="0.8s"/>

The sensitivity (S) of the sensor depends on the size of the diaphragm, the mechanical properties of the diaphragm material, and the piezo-resistive coefficients of the polysilicon (i.e. the fractional change in resistance per unit stress).

The change in resistance ( delta) of one polysilicon resistor can be expressed as:

Equation eleven.

Where zero is the reference resistance of the resistor, is the longitudinal piezo-resistive coefficient of the polysilicon; is the longitudinal stress experienced by the resistor; is the transverse piezo-resistive coefficient; is the transverse stress.

The resistors are designed and placed on the diaphragm such that their transverse stress is negligible, and longitudinal stress dominates. Therefore, for resistors at the edges of the diaphragm and experiencing the maximum compressive stress, their resistance change ( delta) is:

Equation twelve.

Similarly, for the resistors at the center of the diaphragm and experience maximum tensile stress, their resistance change ( delta) is:

Equation thirteen.

The output voltage from the full Wheatstone bridge is: V-out equals V-in over two R-naught, times the quantity delta R edge minus delta R center, which equals V-in over two, times the quantity pi-sub-l sigma-max minus pi-sub-l sigma-center (fourteen) The maximum tensile stress and the maximum compressive stress of a rectangular diaphragm have been well studied and their values depends on the diaphragm structure and mechanical properties, proportional to the applied pressure on the diaphragm ( delta) for small deflections. For a rectangle with half-width "a" and half-length "b" (b greater than or equal to a). The internal geometry coefficients are, and two, which are function of some geoparameters that can be found from literatures.

Equation fifteen.

Equation sixteen.

Where h is the diaphragm thickness ( approximately three hundred micrometers) The differential output signal () and the theoretical sensitivity of the sensor are then

Equation seventeen.

Equation eighteen.

Where () is the offset of the bridge, which is un-avoidable because the micro-fabrication processes are not ideal.

For accurate measurements, each micro-tensiometer needs to be calibrated to get its experimental sensitivity and offset.

less than span id equals "page-thirty-two to zero" greater than II.D.four. Stability.

<break time="0.8s"/>

The stability of the micro-tensiometer are determined by the maximum capillary force the nanoporous silicon can hold, or by homogeneous nucleation or heterogeneous nucleation due to impurities inside the liquid.

The maximum capillary pressure depends on the pore size of the porous silicon membrane, based on equation (one). The pores we have range from two nm to four nm in radius. The typical contact angle between the liquid water surface and the oxidized hydrophilic silicon surface is about twenty-five degrees. The surface tension of water is about seventy-two point four millinewtons per meter at standard temperature and pressure. Theoretically, this pore size range allows a meniscus to hold minus seventy megapascals to minus one hundred thirty megapascals of tension, which is much less negative than the theoretical prediction of the tension (minus one hundred forty megapascals) to create a vapor bubble nucleation in pure liquid water. For individual sensors, the stability limit may be less negative than the prediction due to the impurities in the liquid water, or the random defects in the porous silicon.

less than span id equals "page-thirty-two to one" greater than II.D.five. Response Time.

<break time="0.8s"/>

The response time represents the time scale for the sensor to respond to a step change in the outside water potential, which is similar to the charging and discharging time constant of a RC circuit. If we treat the internal liquid and diaphragm together as the controlled system, and assume that the water transport inside the porous silicon membrane has reached steady state much faster than the internal liquid, we can get the following governing equation for the mass balance of the liquid

Equation nineteen.

Where V is the total liquid volume; is the volumetric flow rate of water through the porous membrane based on Darcy's law:

Equation twenty.

Where three minus is the effective hydraulic conductance of the porous silicon membrane.

The effective bulk modulus ( ) of the diaphragm-liquid system is

Equation twenty-one.

Where is the initial volume of the liquid reservoir.

The governing equation can be translated into a pressure diffusion equation:

Equation twenty-two.

The hydraulic capacitance of the sensor () is

Equation twenty-three.

The hydraulic resistance of the sensor is

Equation twenty-four.

The response of the sensor is psi liquid equals psi vapor plus the quantity psi liquid naught minus psi vapor, times the exponential of negative t over R-effective C-effective (twenty-five) Where,zero is the initial liquid water potential.

The response of the sensor can be treated as a RC circuit with a time constant ( ) of

Equation twenty-six.

i. Hydraulic Capacitance of the Rectangular Diaphragm.

<break time="0.8s"/>

If we treat the effective bulk modulus of the diaphragm-liquid system as springs-in-series fifty-four, we have

Equation twenty-seven.

Where B sub d is the bulk modulus of the diaphragm; bulk modulus of liquid water (B sub w) equals two point two times ten cubed megapascals is the bulk modulus of liquid water.

The bulk modulus of the rectangular diaphragm is calculated from the energy of deflection (E sub def):

Equation twenty-eight.

Equation twenty-nine.

Where coefficient associated with energy of deflection (C sub def) is the coefficient associated with energy of deflection; D N times m is the stiffness of the diaphragm; E Pa is the Young's modulus of the diaphragm; v equals zero point two seven is the Poisson's ratio for the silicon diaphragm used in the micro-tensiometer.

C sub def for different diaphragm shapes can be found in Taylor and Govindjee two thousand four to the power of fifty-five through simulation using numerical methods.

By definition, the bulk modulus of the diaphragm

Equation thirty.

We can get the capacity (K) of the diaphragm:

Equation thirty-one.

Equation thirty-two.

Where delta P d is the pressure on the diaphragm; deflected volume (V sub d) is the deflected volume due to the pressure Based on the fundamental definition of work done by an external force on a system in thermodynamics, the amount of work (energy) required from no deflection to a deflected volume of V sub d can be expressed as:

Equation thirty-three.

Where V sub d,f is the final deflected volume due to delta P d.

Combining eq. (thirty-two) and (thirty-three), we have:

Equation thirty-four.

The volumetric deflection of the diaphragm () can be obtained by modifying eq. (thirty-four):

Equation thirty-five.

Therefore, based on equation (thirty-one) and (thirty-six)

Equation thirty-six.

Combining equations (thirty-seven) and (twenty-eight)

Equation thirty-seven.

ii. Hydraulic resistance of the Synthetic Xylem.

<break time="0.8s"/>

The hydraulic resistance of the sensor has been significantly reduced by introducing the synthetic xylem veins structure. The design of the synthetic xylem veins was based on the idea of the how the cavitation was prevented from spreading in the xylem tissue of woody plants which is under negative pressure \(Figure II-six\) (#page-thirty-six to one).

The hydraulic path defined by this structured membrane can be represented by the circuit diagram in Figure II-six- (#page-thirty-six to one)b. The hydraulic resistance of each element in the circuit can be calculated using the following equation:

Equation thirty-eight.

Where x represents one to three; equals five is the thickness of the porous silicon membrane; is the width of the cross-sectional area for the water transport; is the active length of the porous silicon membrane separating adjacent veins; is the permeability of the porous silicon membrane; ∙ is the viscosity of water; equals zero point four five is the porosity of the porous membrane. Since one and two have the same values, is replaced by one in the following calculations.

Figure II-six The Hydraulic Resistivity of the Synthetic Xylem on Membrane less than span id equals "page-thirty-six to one" greater than (a) The hydraulic resistivity diagram of the repeated paths connecting the internal cavity to the evaporative surface. The water flow from point A to point B through a porous silicon membrane with a depth of five micrometers, a width of one,and a length of one. The water flow from B to C through a membrane with a five micrometers thickness, two width and two in length. The water flow from C to D through a membrane with a five micrometers thickness, three width and three in length (b) Simplified diagram for the study of hydraulic resistivity.

The hydraulic resistance of the synthetic xylem membrane system is R-effective equals R A D equals one over n, times the quantity one-half over R-one plus one over one-half R-one plus R-two plus R-three, which simplifies to one over n times the quantity three-tenths R-one plus R-three (thirty-nine) Where n is the number of the repeated of the motif of veins. The theoretical and experimental comparison of the response time and sensitivity are shown in Table III-one. (#page-fifty-two to zero)

less than span id equals "page-thirty-six to zero" greater than Vapor and Tissue Psychrometric Effect during Measurements.

<break time="0.8s"/>

The water potential of a sample depends on its temperature. The temperature difference between the sensor and the sample creates an error in measured water potential due to the difference in their reference state of zero water potential. As discussed in Section II.B.one, (#page-fifteen to one) the water potential measures the energy deviation of a sample from that of pure liquid water at the temperature and pressure of the sample of interest. We call this error is psychrometric effect.

Figure II-seven Illustration of Vapor Psychrometric Effect less than span id equals "page-thirty-seven to zero" greater than We assume isothermal conditions most of the time. However, in situ applications are always non-isothermal. When measuring a plant tissue, for example, a vapor gap exists between the sensor and the tissue due to the non-uniform contact surface as illustrated in Figure II-seven. (#page-thirty-seven to zero) The temperature, vapor pressure and water potential of the sensor are, and, while those for the tissue are, and. The vapor gap in between has a vapor pressure of. We assume

Equation forty.

Equation forty-one.

Where is the small temperature difference between the tissue and the sensor.

Based on M V L E,

Equation forty-two.

Where

Equation forty-three.

Therefore,

Equation forty-four.

less than span id equals "page-thirty-nine to zero" greater than III. MATERIALS and METHODS.

<break time="0.8s"/>

less than span id equals "page-thirty-nine to one" greater than Micro-Tensiometer Preparation.

<break time="0.8s"/>

less than span id equals "page-thirty-nine to two" greater than III.A.one. Substrates.

<break time="0.8s"/>

Silicon wafers were p-type double side polished wafers with one hundred mm diameter and three hundred fifty plus or minus twenty-five micrometers thickness (Addison addisonengineering.com). They had one-one-one crystal orientation crystal orientation and one minus ten ∙ resistivity; and were selected for porous silicon membrane etching with desired pore size and structure (interconnected structure with pore radius range from two nm to four nm). Double-side polished Borofloat thirty-three glass wafer with one hundred mm diameter and five hundred micrometers thickness, were used to bond with the backside silicon wafer through anodic bonding (University Wafer universitywafer.com) The bonding in the Cornell NanoScale Science and Technology Facility (C N F) (Cornell NanoScale Science and Technology Facility) clean room created an enclosed reservoir for liquid water with reduced impurities; after bonding, the internal cavity was only connected to the outside through the porous silicon membrane.

less than span id equals "page-thirty-nine to three" greater than III.A.two. Fabrication.

<break time="0.8s"/>

A micro-tensiometer requires double side fabrication on a silicon wafer. The backside has etched cavities for the water reservoir and etched nanoporous silicon membrane, and is bonded with a glass wafer. The frontside has a platinum resistance thermometer (P R T) and a Wheatstone bridge (B R). A B R is composed of polysilicon resistors, platinum wires and pads. The whole bonded wafer needs to be diced into five mm x five mm chips accurately at designated positions to get micro-tensiometers. The fabrication processes below were presented in a chronological order. The steps presented below are labeled in Figure III-one- (#page-forty to zero)a.

less than span id equals "page-forty to zero" greater than Figure III-one Preparation of a Micro-tensiometer.

- (a) An Illustration Micro-Fabrication Processes. (Courtesy of Michael Santiago) - (b) A Diagram of The nano-scale porous silicon membrane etching bath. sixty-one - (c) A Diagram showing A micro T M mounted to the printed circuit board (P C B) board with external wires for datalogging. The pads are connected to the P C B board through wire-bonds. The internal cavity connects to the outside vapor through nano-porous silicon.

Steps i and ii: Growth of silicon dioxide (S i O two) Insulation Layer.

<break time="0.8s"/>

After metal-oxide-semiconductor (M O S) clean for the silicon wafers, the eight hundred nanometer S i O two insulation layer was grown into silicon wafer by using the MRL Thermal Oxide Furnace through oxidation. The S i O two insulation is important because the silicon wafer is conductive to electronics, and would disturb the operation of the polysilicon resistors. The oxidation was a batch process, and twenty-five to fifty wafers were able to be processed at the same time. The resistivity of the silicon wafers was checked before the oxidation process using CDE ResMap four-pt Probe. The wafers were first M O S cleaned and then oxidized in the furnace using wet oxygen and nitrogen flow mixed with hydrogen chloric acid at one thousand degrees C for two hundred minutes. To ensure the uniformity of the grown S i O two, baffle wafers were used at the first and the last position of the series of wafers, hydrogen chloric acid was added to the oxygen flow to ensure good oxide quality at a high growth rate, and to help prevent defects in the oxidation layer.

Step iii: Deposition of Polysilicon Layer Deposition.

<break time="0.8s"/>

An eight hundred nanometer thick polycrystalline silicon layer with a boron doping level of six times ten to the nineteenth per cubic centimeter was deposited on top of the S i O two insulation layer in MRL low-pressure chemical vapor deposition (L P C V D) Polysilicon furnace. This high doping level was chosen to optimize the signal and minimize the temperature effects. The deposition was done with a feeding rate of two hundred seventy standard cubic centimeters per minute of one point five percent diborane and ninety standard cubic centimeters per minute of thirty percent silane at six hundred twenty degrees C for one hundred thirty minutes. The polysilicon layer was then annealed in MRL M O S Clean Anneal with Inert gas (argon) at nine hundred degrees C for thirty minutes. The polysilicon-S i O two layer were checked in Filmmetrics for their thickness, and in CDE ResMap four-pt Probe for their resistivity.

Step iv: Patterning of Polysilicon Resistors.

<break time="0.8s"/>

The polysilicon resistors were fabricated using photolithography with S one eight two seven photoresist and dry etching. The pattern of the resistors was generated using the general photolithography process with the mask for resistors. The patterned wafers were etched using Oxford eighty-one Plasma Etcher with SiF six over O two (one hundred twenty-five millitorr, forty-five standard cubic centimeters per minute SF six, fifteen standard cubic centimeters per minute O two, one hundred W). The radio frequency (R F) plasma dissociated SiF six into fluorine (F\) and other fragments. F and Si reacted to form silicon tetrafluoride or silicon difluoride products because Si-F has stronger bond than Si-Si. Oxygen kept fluorine concentration high, prevented them from recombination their dissociated fragments, and led to stable end products of plasma etching. The etching depth was checked using P one zero Profilometer (P one zero ). The etching was stopped when the color of S i O two layer appeared blue over purple over green, because S i O two with different thickness shows different color. (BYU clean room, the link in the text )

Step v: Patterning of S i O two.

<break time="0.8s"/>

The S i O two insulation layer was fabricated using photolithography (S one eight two seven ) and dry etching. After the wafers were patterned with the mask for S i O two patterning, the patterned wafer was dry etched in Oxford eighty-one using trifluoromethane over O two (fifty millitorr, fifty standard cubic centimeters per minute C H F three, two standard cubic centimeters per minute O two, two hundred W) for twenty minutes, which depends on the etch rate measured by P one zero. C H F three over O two has higher selectivity against silicon, which is favored in this case. The end products were S i F four and C O two, which had stronger bonds than Si-O bond. The etching was stopped when the color of the Silicon wafer appeared. The fabricated resistors had a typical resistance of two thousand ohms. Figure II-five- (#page-twenty-eight to zero)e shows the shapes of the resistors.

Steps vi and vii: Patterning of Backside Cavity.

<break time="0.8s"/>

The backside cavity was created by dry etching three micrometers into the silicon wafer. The S i O two and polysilicon layers on the backside were removed using the same dry etching method for their fabrication. The residues were removed using a dip in buffered oxide etch (B O E) six:one (buffered H F etch). The backside cavity was patterned using the designated mask with S one eight two seven. The etching was done in Oxford eighty-one using SF six over O two mentioned above. The etching rate was controlled using P one zero.

Steps viii to xi: Backside Patterning and Etching of Porous Silicon.

<break time="0.8s"/>

The porous silicon membrane was patterned through general photolithography using the AZ P four nine zero three thick photoresist (six micrometers). This photoresist protected the un-exposed area from etching in electrochemical bath during Anodization. The porous silicon etching was done in an electrochemical etching bath shown in Figure III-one- (#page-forty to zero)b. The electrolyte was a mixture of concentrated H F (forty-nine percent H F Aqueous solution, Sigma Aldrich). and Non-Denatured Ethanol (Sigma Aldrich). (Safety Warning: H F is corrosive and contact poisonous; Working with H F requires personal protection equipment) The cathode was a platinum pad. The aluminum was deposited conformally on the frontside of the silicon wafer to make electrical contact with the aluminum anode by using the CHA Mark five zero Evaporator of NBTC (Cornell Nano-biotechnology Center) in the clean room. To prevent electrolyte corrosion of the aluminum, a cylindrical poly-tetra-fluoro-ethylene (P T F E) (poly-tetra-fluoro-ethylene) Chamber with seventy-six mm diameter was used on top of the wafer for the electrolyte. The leakage was prevented by using a Viton O-ring between the chamber and the wafer, and by enhancing the contact using screws. The current density was set to twenty milliamps per centimeter squared with Hewlett Packard DC power supply (Model six thousand six hundred thirty-four B). The etching duration was five minutes at one micrometer per minute, which resulted in an expected membrane thickness of five micrometers. After etching, the wafers were washed using deionized water (D I) and dried in a desiccator to allow the evaporation of H F from the porous silicon, and prevent corrosion. The aluminum on the frontside was removed using AZ three hundred MIF developer to prepare for further fabrication of electronics.

The pores of the etched membrane were then oxidized using Rapid Thermal Anneal (R T A, AG Associates Model six hundred ten) at seven hundred degrees C in pure oxygen for thirty seconds with ten degrees C per second ramping. The oxidation of the porous silicon creates Si-O bonds on the silicon surface, and made the pores more hydrophilic, which resulted in higher sensor stability.

Step xii: Backside Silicon Wafer Anodic Bonding with Glass Wafer.

<break time="0.8s"/>

The bonding was done in vacuum at four hundred degrees C using one thousand five hundred V DC in SUSS SB eight e Substrate Bonder (SUSS). Both glass wafers and silicon wafers were thoroughly cleaned before bonding to minimize the organic residues on wafers, which is crucial for sensor stability. The glass wafers were cleaned in nanostrip (ninety percent sulfuric acid, five percent peroxymonosulfuric acid and less than one percent hydrogen peroxide). The silicon wafers were cleaned using organic solvents acetone and isopropyl alcohol (I P A), followed by D I water rinse and drying. The silicon wafers were not washed using nanostrip because the nanostrip could damage the etched P o S i. The wafers were then descumed in Anatech using oxygen plasma before bonding. The vacuum environment in the bonder prevented wafer contamination. The four hundred degrees C bonding temperature softened the glass, and made it conform on the silicon for irregularities, which improved contact. The high temperature also dissociates the sodium oxide in glass into sodium ions (Na two +) and oxygen ions (O two-). The positive voltage on the silicon drove the O two- migration towards the bonding surface and created Si-O bonds at the surface, which enhanced the bonding strength.

Step xiii: Fabrication of Frontside Electronics.

<break time="0.8s"/>

The wafers were deposited with titanium, fifteen nanometers, over platinum, two hundred nanometers, over titanium, fifteen nanometers, metal layers through lift-off in CVC E-gun Evaporation System (CVC, model SC four five zero zero ). The electronics were patterned using the mask for electronics with LOR five A and S one eight two seven photoresists. The exposed area on the wafer (S i O two insulation layer) were descumed using Anatech to ensure better contact with the metal. The Titanium layers at the bottom and the top of P t enhanced the adhesion of metal with the S i O two insulation layer at the bottom, and with the passivation layer at the top (discussed below). The rate and thickness of deposition were monitored through CVC directly.

The lift-off was done using the LOR remover, one-methyl-two-pyrrolidinone (one thousand one hundred sixty-five, provided by C N F), in sixty degrees C while sonicating for thirty minutes. Another thirty min of sonication was done to ensure clean removal of all photoresists. The wafers were then rinsed using D I water and dried.

The resistances of the Wheatstone bridge and the P R T were checked using the IV probe station in the C N F clean room, with expected values to be two thousand ohms and one thousand five hundred ohms respectively. The contact resistance and linearity between the electronic wires and the polysilicon resistors were checked as well.

Steps xiv and xv: Deposition of Frontside Passivation Layer.

<break time="0.8s"/>

The passivation layer was deposited to protect the electronic on the wafer. The wafers were cleaned in organic solvents acetone and I P A and descumed in Anatech to better adhesion. The passivation layer was composed of four hundred nm S i O two, three hundred nm silicon nitride (S i N x), two hundred nm of oxynitride (silicon oxynitride (S i O N)), and one hundred nm of S i O two in order at two hundred degrees C in Oxford plasma-enhanced chemical vapor deposition (P E C V D). The duration for each component was calculated based on the deposition rate set in the P E C V D.

The contact pads for external wiring were opened through photolithography (S one eight two seven ) using the mask for contact pads opening, and dry etching using C H F three over O two in Oxford eighty-one. The possible residues of S i O two and T i on the opened pads were cleaned using brief dip in B O E thirty:one.

The resistances and linearity of the electronics were checked again in the IV probe station. The photoresists were cleaned using organic solvents followed with D I rinse and drying.

Step xvi: Dicing and Labeling of Sensor.

<break time="0.8s"/>

The wafers were diced using DISCO Dicing Saw with an all-purpose blade that cuts the glass-silicon bonded wafer. The dicing was done accurately based on the dimensions of the sensors (five mm x five mm) and the position of the porous silicon membrane. The sensors were labeled from one to two hundred thirty on a single wafer. The wafers were labeled alphabetically based on the order they were fabricated. For example, the P one eight seven device used below was the number one hundred eighty-seven device from P wafer.

Steps xvii to xix: External Wiring and Packaging.

<break time="0.8s"/>

The sensor chips need to be wired up to send signals outside. The external wiring for the sensor is composed of the wire-bonding between the chips and the printed circuit board (P C B, oshpark.com), and the wires soldered to the P C B for external data acquisition \(Figure III-one- (#page-forty to zero)c).

Since the wirebonds were the weakest part of a packaged micro T M, the copper contact pads on the P C B board were designed so that minimum number of wirebonds were needed and the shortest wirebond length was needed between the pads on micro T M and the copper pads on the P C B. The copper pads were connected to the outside by soldering external wires to the holes designed on the P C B board, as illustrated in Figure III-one- (#page-forty to zero)c.

To add external wires, the chips were first glued onto the P C B boards using the five min set epoxy (LOCTITE). The Wire-bonding connected thirty-two micrometers-thick aluminum wires between the contact pads and the P C B board, and was done using the WESTBOND seven thousand four hundred A ultrasonic wire bonder from the C N F. The P C B board were soldered with external wires, which could be connected to an external datalogger (CR six from Campbell Scientific).

The packaging is important to protect the sensors from external corrosion and possible damage during use. The wire-bonds, which were the most fragile part due to the thin wires and delicate bonding to pads, were potted with a material designed for wire-bonding (nine thousand one-E-v three.one, DYMAX). This material had features of fast curing and small stress on wire-bonds. After applying the material on the wire-bonds, the nine thousand one was cured for thirty-five minutes using three hundred sixty-five nanometer wavelength and three thousand microwatts per centimeter squared intensity UV light (SPECTROLINE, Model BIB-one hundred fifty P), followed by fifteen min heat cure in one hundred fifty degrees C. The whole sensor-P C B system were packaged using polyurethane resin UR five zero four one (ELECTROLUBE) with high tear resistance and osmotic solution resistance to protect the sensors from external stress during applications and the electronics from external corrosion by osmotic solution. The resin and the hardener of UR five thousand forty-one were mixed in a weight ratio of three point six four to one before use. The curing was twenty-four hours at room temperature. To facilitate handling and insertion, the encapsulation was done by potting the sensor-P C B in a proper size garolite tube (McMaster-Carr). This tube material has as high of a tensile strength as metal tubes, but much lighter. The encapsulation strategy may vary due to the experiment purposes, as shown in Section III.B.three.i. (#page-fifty-six to one)

less than span id equals "page-forty-seven to zero" greater than III.A.three. Bridge Calibration and Stability.

<break time="0.8s"/>

The electronic signal needs to be translated into mechanical signal through calibration. Each sensor needs to be calibrated before being put into use. The calibration was done against a precise pressure gauge (Honeywell, TJE model, thirty-four megapascals). The sensors were first filled with water using a high pressure chamber (H I P High Pressure Equipment Company, Model thirty-seven to six-thirty) at about three point four five megapascals for six hours \(Figure III-two- (#page-forty-nine to zero)a.). Once filled, the sensors were connected to the CR six datalogger, while letting the sensor cavitate. The maximum output from the sensor before cavitation was taken to be the stability limit of the sensor, and could be translated into pressure data after calibration. After cavitation, with the cavity empty but the P o S i was still wet, the micro T M was put into a high-pressure chamber immediately. This chamber was connected to a compressed pure nitrogen gas cylinder (Airgas) through a regulator valve. After the compressed nitrogen gas was fed into the cylinder, the cylinder gas pressure was sensed by the Honeywell pressure gauge \(Figure III-two- (#page-forty-nine to zero)b & d). The P o S i was kept wet during the entire calibration process because the menisci block entry of gas into the cavity; the capillary pressure of the menisci held the pressure difference between inside cavity and outside as the outside gas was pressurized. This pressure difference was sensed by the micro T M through the deflection of the diaphragm, as presented in Section II.D.two. (#page-thirty to zero) The sensor reading was then calibrated against Honeywell output for each stepchange of gas pressure. Since gas temperature went up every time more gas was filled into the pressure chamber, and relaxed back to room temperature after about several minutes, both P R T and bridge output were recorded during the bridge calibration, and the duration for each pressure step was long enough for temperature relaxation.

Based on the discussion above, we had a theoretical calibration for the sensor output

Equation forty-seven.

Where and are calibration coefficients only for the pressure-dependent term (()), and and are calibration coefficients only for the temperature dependent term (()).

less than span id equals "page-forty-nine to zero" greater than Figure III-two Sensor Filling, Bridge and P R T Calibrations Illustrations.

(a) Sensor filling system. Sensors are filled using high pressure water ( ~three point four five) for greater than six hours. sixty-four (b) Sensor calibration set-up. The sensors are calibrated using step-change of gas pressure from a compressed nitrogen cylinder monitored using a Honeywell pressure gauge (PH). The response of the Wheatstone Bridge (B R) and P R T is monitored through CR six datalogger. (Modified from Pagay two thousand fourteen sixty-four) (c) Temperature control water bath for B R offset and P R T calibration: The sensor response is calibrated against a step-change of the water bath temperature. (d) Pressure calibration curves for two sensors labeled with difference colors. The slope of the line regression is the sensitivity of the sensor. The intercept with the y-axis was the offset (e) B R offset calibration curve for three sensors labeled with three different colors. The slope of a curve was the B R temperature sensitivity. The intercept was the offset of the B R at fifteen degrees C. (f) P R T calibration curve for three sensors labeled by three different colors. The slope and intercept were calibration parameters for a P R T. Different calibration coefficients specified for each diaphragm size is shown in table III.one. (g) Temperature Corrected Sensor Response. The temperature corrected response from the micro T M due to a fifteen degrees C temperature change was minus zero point three five bar. The peak at the beginning proved a functioning micro T M by responding to air water potential.

To correct for the temperature effect on the bridge output, the bridge offset was calibrated against temperature for and. The calculation of and is presented in the following section.

less than span id equals "page-fifty to zero" greater than III.A.four. The Bridge and P R T temperature calibration.

<break time="0.8s"/>

Since material properties change with temperature, the bridge offset and P R T response were calibrated against temperature using a temperature-controlled water bath (Fisher Scientific). The calibration set-up was shown in Figure III-two- (#page-forty-nine to zero)c.

Based on the temperature calibration data, we got the P R T calibration curve (()), as well as the bridge offset dependence on temperature (zero (), Eqn. (forty-nine)).:

Equation fifty.

Where and were P R T calibration coefficients. The calibration parameters for Eqn. (forty-nine) and (fifty) could be obtained from Figure III-two- (#page-forty-nine to zero)e and f.

The () term can be calculated as below: V out(P) equals V out(P,T) - V out,zero(T) equals V out(P,T) - (m BT P R T(T) - b T over m T + b BT) (fifty-one) The experimental and could now be obtained by plotting () against ℎ where the temperature dependence of the Honeywell was ignored (five times ten to the negative fourth megapascals per degree Celsius). In other words, the and may have some dependence on temperature, but this effect has been neglected in current studies.

During the use of the sensor, we measured the () and () output directly from the sensor. The temperature and pressure can be easily calculated from the two equations below:

Equation fifty-two.

Equation fifty-three.

less than span id equals "page-fifty-one to zero" greater than III.A.five. Response Time Testing Through Osmotic Potential Measurement.

<break time="0.8s"/>

As discussed before, the response time is the time constant for a sensor to respond to a step change in the sample water potential (Eqn. twenty-six and twenty-seven). To test the response time, a micro T M was calibrated using the positive pressure gas cylinder method shown in Figure III-two- (#page-forty-nine to zero)a. The measuring tip of the micro T M was protected using an expanded P T F E membrane (e P T F E, Porex, PMV one zero ). The P T F E membrane only allowed vapor, not liquid water, to diffuse through. Figure (#page-fifty-one to one) III-three- (#page-fifty-one to one)b showed the plot of the sensor response to a minus nineteen point one osmotic solution through the e P T F E

less than span id equals "page-fifty-one to one" greater than Figure III-three Measurements in Osmotic Solutions: micro T M Response Time Scale and Accuracy.

(a) Diagram of the packaged sensor tested for the osmotic response. (b) Plot of the sensor response to a step change from pure liquid water to a minus nineteen point one bar sucrose solution in isothermal water bath (twenty-five degrees C). The dashed red line represents the offset of the sensor reading was minus zero point seven bar. The solid red line represents the final reading by the micro T M. The dashed black line represents the osmotic potential (minus nineteen point one bar) measured by the chilled mirror hygrometer. The time constant ( tau ) for this response was about two min.

membrane. The micro T M was kept in pure water at the beginning, and was then removed from the pure water, briefly held in the air, and submerged in the sucrose solution (Sigma-Aldrich). The activity of the solution was checked using a Chilled-Mirror hygrometer (Decagon WP four C). The tensiometric measurement was done in an isothermal water bath to prevent psychrometric effect in the e P T F E membrane, as discussed in Section II.E. (#page-thirty-six to zero) In Figure III-three- (#page-fifty-one to one)b, after removing the offset, the micro T M showed a zero point two megapascals lower water potential than the WP four C. This difference was larger than the error range of WP four C ( plus or minus zero point zero five megapascals for zero to minus five megapascals range). The possible reasons are: one) the error comes from the Honeywell Pressure sensor, against which the B R was calibrated; two) the water adsorbed onto the sensor was brought into the solution and diluted the osmotic solution. Further testing needs to be done to clarify the reason for the difference.

Table III-one (#page-fifty-two to zero) shows typical response times, pressure sensitivities, and temperature sensitivities, and stability for different diaphragm sizes measured through experiments, and predicted based on the theory discussed in Section II.D. (#page-twenty-seven to zero) The measured transient time if about two orders of magnitude larger than the predicted transient time. Since the transient time was measured experimentally using an osmotic solution with known water potential, the solutes might have accumulated in the P o S i and increased the hydraulic resistance of the porous silicon less than span id equals "page-fifty-two to zero" greater than Table III-one Transient, Sensitivity and Temperature Sensitivity of the Micro-Tensiometers layer. Another possibility is that a boundary layer exists due to the loss of water from the porous silicon membrane to the neighboring solution and diluted the solution locally. The characteristics of the porous silicon membrane might also be changed due to the storage environment or the solution and resulted in change in its hydraulic resistance. Among the three major diaphragm sizes, the one times two device has the fastest response time, but smallest sensitivity and the largest temperature sensitivity, while the two times three point five device has the slowest response but the best sensitivity and minimum temperature sensitivity. The properties of the one point five times three devices lie in between those of the one times two and two times three point five devices. Although, one times two devices typically had the highest stability, and two times three point five devices had the lowest stability, the stability limits varied significantly from device to device and should be confirmed before application.

Table six. This table reports how diaphragm size affects the sensitivity, bridge temperature sensitivity, and stability of a pressure sensor across different measurement conditions.

less than span id equals "page-fifty-three to zero" greater than Greenhouse Experiments.

<break time="0.8s"/>

less than span id equals "page-fifty-three to one" greater than III.B.one. Apple Trees Growth Information.

<break time="0.8s"/>

The apple trees (MAH-lus doh-MES-tih-kah) were grown in the Yellow Greenhouses on Cornell Campus. They were two point five to three point zero m in height, with trunks three cm to four cm in diameter. They were moved from the Cornell Orchard in pots on Feb. tenth, two thousand sixteen. There were three trees in a row, separated by about one m from each other. The distance between rows were about three m, and we had three rows in total. Experiments were done from the beginning of April two thousand sixteen to the end of June two thousand sixteen. Greenhouse experiments GH one and GH three were trial experiments, whose data are not presented in this thesis. The second greenhouse experiment (G H two) was from April eighth, two thousand sixteen to May sixth, two thousand sixteen. The fourth greenhouse experiment (G H four) was from May twenty-sixth, two thousand sixteen to June twenty-sixth, two thousand sixteen. The trees were well-watered before experiments. They had apples growing during the two experiment periods. (We acknowledge Dr. Lailiang Cheng for the apple trees)

less than span id equals "page-fifty-four to zero" greater than III.B.two. Greenhouse Experiment two (G H two).

<break time="0.8s"/>

i. Devices and Data Acquisition.

<break time="0.8s"/>

One micro T M (M four five ) was used in G H two. A Scholander pressure chamber (SOILMOISTURE Equipment Co.) was used to measure the stem water potential as a benchmark for the sensors. (We acknowledge Dr. Alan Lakso for the pressure chamber.) The packaging strategies of the micro T M are shown in Figure III-four. (#page-fifty-five to zero) The G H two data were logged with a CR six powered by a sealed rechargeable battery BP seven (twelve V, seven Ah) from Campbell Scientific. A program was written using CRBasic (datalogging programmer by Campbell Scientific) to excite the bridges by two hundred millivolts, and the PRTs by two hundred microamps, every thirty seconds. The program is shown in Appendix \(VIII.B\) (#page-ninety-five to zero). Related weather data including solar intensity were gathered from Network for Environment and Weather Applications (N E W A) from Ithaca Cornell Orchard weather station \( the link in the text ).

less than span id equals "page-fifty-four to one" greater than ii. Sensor Installation and Insulation.

<break time="0.8s"/>

For round packages, the micro T M was installed into the trees by drilling one cm deep holes perpendicularly into the tissue below the bark \(Figure III-five- (#page-fifty-seven to zero)i). The packaged sensors were nine point six mm in diameter. A large guide hole was made by using a ten mm Jobber's Drill Bit (McMaster), followed by a grinded-down flat tip nine point five mm Jobber's Drill Bit, to create a flat bottom for better contact between the sensor tip and the tissue. The holes were wetted using tap water after drilling. Since wet wood shrinks after drilling, the size of the drill bits were selected to fit the size of the packaged devices without large gaps. The sensors were pressed into the hole gently. After the sensors were embedded, they were sealed with caulk (McMaster three zero zero eight K one three ) to prevent water loss. The thermal insulation was done by using three point one eight mm-thick neoprene foam sheets (McMaster eight six four seven K eight one ) tightly wrapped around the sensors, followed by wrapping the sensor and the tree together using one point two seven cm-thick Ultra-Flexible Foam Rubber (McMaster nine three four nine K two ).

Figure III-four Set-up Illustration for Greenhouse Experiments less than span id equals "page-fifty-five to zero" greater than (a) Diagram showing the mu TMs used for the greenhouse experiments. The encapsulation material for all sensors was polyurethane. All wire-bonds were protected by nine thousand one modified polyurethane material designed for wire-bonds. P two zero was fully encapsulated in a glass tube, with a e P T F E membrane as a vapor gap between the sample and the sensor. P one seven six was only fully encapsulated in a garolite tube. P one seven nine was potted up to the wire-bonds, but the garolite tube covered up to the membrane. P one eight seven was encapsulated up to the wire-bonds. M four five was packaged in a longer tube due to a longer P C B board (the length was not shown here). (b) Diagram showing that G H two had M four five installed. (c) Diagram showing that G H four had six mu TMs. P three six did not have a working bridge, so it only sensed temperature. The sensors on the stem were installed ten to fifteen cm separated from each other, and rotated around the stem. The M P S-six and M four five were installed in the soil to monitor soil water potential.

Large plastic bags were used to cover the foam as a waterproof layer, and was tightly sealed using zip-ties against the trees. The whole thermal insulation (about ten cm-thick) was covered by aluminum foil as a reflective insulation to prevent sunlight from heating up the sensor and the insulation system.

iii. Pressure Chamber Measurements.

<break time="0.8s"/>

The leaves were wrapped in aluminum foil covered with plastic bags for at least twenty min before they were cut and pressurized \(Figure III-five- (#page-fifty-seven to zero)viii). This method gave us stem water potential measurements.

The pressurization on the leaves were stopped when bubbling started to come out of the cut stem. The bubbles would usually form a liquid droplet after a couple of seconds. The pressurization would be continued if the bubbling stopped and no liquid droplet formed. A pressure bomb measurement was done on a single leaf for each time point.

less than span id equals "page-fifty-six to zero" greater than III.B.three. Greenhouse Experiment four (G H four).

<break time="0.8s"/>

less than span id equals "page-fifty-six to one" greater than i. Devices and Data Acquisition.

<break time="0.8s"/>

Seven devices were used in G H four, including five micro-tensiometers (P two zero, P three six, P one seven six, P one seven nine and P one eight seven ) in the tree, and one micro-tensiometer (M four five ) and one M P S-six (Decagon) in the soil. The packaging strategy for the six micro-tensiometers are shown in Figure III-four. (#page-fifty-five to zero) The size of packaged sensors was nine point six mm in diameter. Some of the PRTs on the sensors were broken during the embedding because the sensor edge was chipped when the sensor was pressed against the tree. The installation strategy and packaging will be improved to avoid damaging PRTs in future experiments. The same Scholander pressure chamber was used to measure the stem water potential as a benchmark for the sensors.

Figure III-five Photos Showing Micro-Tensiometer Installation and Insulation (G H four) less than span id equals "page-fifty-seven to zero" greater than (i) A drilled hole in a living tree; (ii) Installation of sensor in a cut branch (a picture of installed sensor in a living tree was not taken to prevent sensor cavitation due to water loss); (iii) Stabilization of sensors using plumber's putty and Parafilm; (iv) Reinforcing sensor-tissue contact using an elastic band; (v) Thermal insulation using polystyrene foam and polyester fiber wrapped into a large plastic bag; (vi) Reflective insulation using aluminum foil; (vii) Opening of a slit using a chisel and a knife for the bare device P one eight seven; (viii) Bagging a leaf with aluminum foil covered bags for stem water potential measurements using the Scholander pressure chamber.

The data from the sensors were gathered through CR six connected with a AM one six over thirty-two B Relay Multiplexer (A M) powered by a BP seven battery. One CR six -A M system was able to operate as many as eight sensors (including one Wheatstone bridge and one P R T per sensor). The M P S-six was powered using the switched twelve V power supply on CR six. The thermocouple was connected directly to CR six to prevent errors due to extra wiring between the CR six and the A M. A program was written in CRBasic to run the devices at the same time, and was shown in Appendix \(VIII.C\) (#page-ninety-eight to zero). The data of the mu TMs were taken every ten seconds as a main program, while the M P S-six data were taken every thirty s as a minor program in parallel. The bridge was excited using fifty millivolts, and the P R T was excited using twenty microamps. Related weather data including solar intensity were gathered from N E W A as in G H two.

less than span id equals "page-fifty-eight to zero" greater than ii. Sensor Installation.

<break time="0.8s"/>

The mu TMs were filled with water at three point four megapascals for greater than or equal to six hours using the HiP high pressure chamber \(Figure III-two\) (#page-forty-nine to zero), and brought to the greenhouse submerged in water. The sensors were connected to the CR six -A M in the greenhouse. Data was taken during the entire installation period. For each sensor, a hole of five mm depth was drilled using a nine point six mm diameter Forstner Bits (McMaster three two one six A two one ). The holes were made in the radial direction with respect to the trunk, and were then wetted using tap water to prevent drying of the tissue around the hole \(Figure III-five- (#page-fifty-seven to zero)i). The P one eight seven device was a bare device with no polyurethane packaging on top of the diaphragm. Therefore, this device was installed by using a chisel and a blade to open a slit vertically below the bark \(Figure III-five- (#page-fifty-seven to zero)vii). This method resulted in less damage to the tissue relative to that induced by the drill. The mu TMs were then inserted into the holes gently \(Figure III-five- (#page-fifty-seven to zero)ii). After installation, the sensors were stabilized using Plumber's Putty sealing cord (McMaster nine four zero eight T one four ), which helped prevent water loss from the hole \(Figure III-five- (#page-fifty-seven to zero)iii). Compared to caulk, the sealing cord provided better mechanical stabilization for the sensors. The sealing cord layer was then wrapped with PARAFILM (Bemis) against the stem as a further stabilization and waterproofing. The contact between the tubular sensors were improved by wrapping an elastic band around the sensor and the tree to hold them together \(Figure III-five- (#page-fifty-seven to zero)iv). The sensors were separated about ten to fifteen cm from each other axially along the trunk, and rotated around the stem to make sure they were not directly on top of one another and blocking the water flow \(Figure III-four\) (#page-fifty-five to zero). Thermal insulation was done using three point one eight mm-thick neoprene foam sheets (McMaster eight six four seven K eight one ), followed by a thick layer of polyester fiberfill (Air Lite five hundred eighty over six). The polyester fiber was then used as the second layer of insulation instead of thick foam sheets in GH one \(Figure III-five- (#page-fifty-seven to zero)v), because the polyester fiber could be easily shaped to provide more intact insulation for the complex geometry of the sensors on the stem. The polyester fiberfill was wrapped in a large plastic bag as in G H four to prevent water loss from the opened plant tissue. The insulation (about twelve cm-thick) was finished with a layer of aluminum foil, which was also applied to cover the soil as the last step \(Figure (#page-fifty-seven to zero) III-five- (#page-fifty-seven to zero)vi). The soil sensors (M four five and M P S-six) were installed in a forty-five degrees angle against the soil surface, to minimize the disturbance on the soil matrix \(Figure III-four- (#page-fifty-five to zero)c). The soil sensors were installed at the end of the first drought period, as shown in Figure IV-two. (#page-sixty-four to zero) Re-watering after the soil sensors installation improved the soil integrity around the sensors. thirty-four

iii. Scholander Pressure Chamber Measurements.

<break time="0.8s"/>

The measurement methods were the same as in G H two except that three pressure bomb repetitions were taken to get a range of stem water potential at one-time point.

less than span id equals "page-fifty-nine to zero" greater than III.B.four. Data Analysis Methods.

<break time="0.8s"/>

The data were analyzed and plotted using MATLAB (MATHWORKS License five hundred fifty-four thousand eight hundred ninety-six). The offset of the mu TMs were calculated and subtracted from the entire data set based on the night water potential upon two days of watering after the first drought period. The appropriateness of this correction will be assessed in future experiments.

less than span id equals "page-fifty-nine to one" greater than III.B.five. Simulation -- Heat Conduction Between the Tissue and the micro T M.

<break time="0.8s"/>

To study the temperature difference between the tissue and the sensor discussed in Chapter IV, a two-dimensional heat conduction model without internal heat generation was built using Finite Difference Methods. In this model, sensors packaged with air or polyurethane (packaged dimension ten mm diameter x twelve mm length) were taken to be in direct contact with the tissue with complete embedding (i.e. the whole sensor tube was inside the tree). The heat flux from plants to the outside air was calculated using a well-studied one D cylindrical heat transfer model. The heat conduction between the tissue and the sensor was simulated using a two D heat conduction model with top, left and right, three boundary conditions as fixed tissue temperature (Tp), and the bottom boundary condition as fixed heat flux to the outside, as calculated using the one-D heat transfer model in a cylinder before. I assumed fixed temperature difference between the plant tissue and the outside air (Tout), therefore equals minus minus represents how close the cavity temperature is to the measured tissue temperature at steady state. The time scale for to reach steady state heat conduction was also recorded.

The program of this simulation is provided in Appendix VIII.E. (#page-one hundred eleven to zero)

less than span id equals "page-sixty-one to zero" greater than IV. RESULTS AND DISCUSSION.

<break time="0.8s"/>

less than span id equals "page-sixty-one to one" greater than G H two.

<break time="0.8s"/>

The purpose of G H two was to explore installation and insulation strategies, and to compare the micro T M readings with those of the Scholander pressure chamber.

The insulation method was developed in G H two to prevent water loss from the drilled holes by using large plastic bags, to minimize the disturbance from the outside temperature variations by adding thick polystyrene foam around the mu TMs, and to prevent sunlight from heating up the sensors by using aluminum foil as reflective insulation. The optimum insulation method was explained in Section III.B.three.ii. (#page-fifty-eight to zero) Even though the greenhouse temperature was controlled, there was still an air temperature variation of plus or minus three degrees C during the day.

In Figure IV-one, (#page-sixty-two to zero) the Scholander reached a peak value at about eleven hundred hours in the morning, while the micro T M reached its peak value at about sixteen hundred hours in the afternoon, when the sensor temperature was increasing at the highest rate. Comparing the midday water potential measured by these two difference methods, the M four five -micro T M reported a fifteen bar more negative water potential than the Scholander \(Figure IV-one- (#page-sixty-two to zero)a). The reason for the mentioned differences might be the vapor psychrometric effect discussed in Section II.E (#page-thirty-six to zero) due to the vapor gap and the temperature difference between the micro T M and the tissue. Notice that in G H two, the sensor-tissue contact was not reinforced using the elastic bands \(Figure III-five- (#page-fifty-seven to zero)iv), a small vapor gap between the micro T M and the tissue could cause significant error (~ eight megapascals over degrees C) (Section II.E\) (#page-thirty-six to zero).

less than span id equals "page-sixty-two to zero" greater than Figure IV-one G H two--Comparison between the Scholander pressure chamber and the micro T M (a) Plot of M four five -micro T M measured water potential, scholander pressure chamber measured potential and temperature measured by M four five -P R T during one diurnal. The left y-axis represents measured negative water potential (-bar). The right y-axis represents the temperature measured by the sensor M four five and has its positive direction pointing downwards. The x-axis is the time-scale during the day in hours. The black line represents the data from M four five. The blue dots are Scholander data. The red line is the temperature measured by the M four five -P R T. The stem water potential decreased during the day, and increased at night. (b) Plot of the measured water potential and the "temperature gradient". The right y axis is the ( T minus T at fifteen minutes prior) equals minus ( T minus T at fifteen minutes prior), which was expected to represent the temperature difference between the micro T M and the tissue in direct contact. It has its positive direction pointing downward.

To study the effect of the vapor psychrometric effect, the possible temperature difference () between the measured sample and the micro T M was estimated by subtracting from the current temperature of the sensor (T) measured by the M four five -P R T, the temperature at an earlier time point. The rational is that when temperature increases at the site of the sensor, we expect that there is a radial gradient of temperature along which heat flows from outside in. We take the rate of change in temperature as the radial gradient. The best correlation between the T and the micro T M happened at a fifteen min time difference, as shown in Figure IV-one- (#page-sixty-two to zero)b, after comparing with the temperature five min, fifteen min, twenty-five min and forty-five min earlier. The temperature dependence of the micro T M was observed in Figure IV-one- (#page-sixty-two to zero)b: the stem water potential measured by the micro T M varied similarly as the ( T minus T at fifteen minutes prior).

Based on the simulation explained in Section III.B.five (#page-fifty-nine to one) (code displayed in Appendix VIII.E\) (#page-one hundred eleven to zero), for a fixed temperature difference between the plant tissue and the outside air ( minus), under steady state heat conduction, approximately zero point five two for a sensor packaged in both polyurethane and air. The higher the, the closer the cavity temperature to the tissue temperature. We expect a low value of, if the sensor was not in good contact with the tissue. This result indicates that a fixed fraction of temperature difference between the sensor and the tissue, which may have resulted in the fifteen bar difference as well as the water potential difference at other times of the day, always exists. The simulation also indicated that the time scale for the cavity temperature to reach steady state in polyurethane was one order of magnitude longer than that for a sensor packaged with air. Therefore, to make the micro T M measurements more accurate, improving the thermal contact between the sensor and the tissue is crucial. Low profile packaging strategies with minimum polyurethane were tested below in G H four.

less than span id equals "page-sixty-three to zero" greater than G H four.

<break time="0.8s"/>

Previous results in G H two motivated the use of multiple packaging strategies in G H four, as described in Section III.B.three, (#page-fifty-six to zero) and shown in Figure III-four. (#page-fifty-five to zero) Figure IV-two (#page-sixty-four to zero) shows the chronological record of the entire experimental period. During the day, the stem water potential recorded by the sensors decreased. At night, the sensors reported a higher water potential. The transpiration stopped at night, and the stem water potential increased to values near those of the soil. The tree went through two drought periods (days one to seven; days eight to twenty-two). Each drought period could be recognized by the decrease in predawn stem water potential measured by the sensors. After rewatering (day seven around three pm, and day twenty-two around eleven am), the predawn stem water potential of the sensors went back to their offset value. Figure IV-three (#page-sixty-five to zero) shows the pictures of the tree before (Day twenty-two) and after rewatering (Day twenty-four). Figure IV-three- (#page-sixty-five to zero)a shows the

less than span id equals "page-sixty-four to zero" greater than Figure IV-two G H four Chronological Record of the Entire Experiment Period This plot includes the entire data for G H four experiment. The left y-axis represents the measured stem water potential. The right y-axis represents the measured sensor temperature with its positive direction pointing downward. The x-axis is the time-scale based on days after the sensor installation. The red lines represent the temperature measured by sensors P one seven six and P one seven nine. The black, green, blue, magenta solid lines represent the micro T M data from P one eight seven, P two zero, P one seven six and P one seven nine respectively. P two zero had a layer of e P T F E membrane between the plant tissue and the sensor. The black dashed line represents the soil water potential measured by M four five. The blue circles with error bars represent the stem water potential measured by the Scholander pressure chamber. The two drought periods were days one to seven and days eight to twenty-two. The dark bars represent the twelve-hour dark period from six pm to six am. All stem sensors (micro T M and Scholander) show that the stem water potential decreased (more negative) during the day, and increased at night. The PRTs measured increased temperature during the day and decrease temperature at night. The first drought period was from day one to day seven. On day seven, several Scholander pressure chamber measurements were done. Rewatering was at two pm on day seven. The soil micro T M and M P S-six were installed on day seven as well. The second drought period was from day eight to day twenty-two. Rewatering was done at eleven am on day twenty-two. More Scholander pressure chamber measurements were done on day twenty-four.

status of the tree when its turgor pressure was significantly reduced due to lack of water. Figure (#page-sixty-five to zero) IV-three- (#page-sixty-five to zero)b shows the status of the tree after its recovery from rewatering. The data from the sensors were offset corrected based on the predawn water potential measured after three nights upon rewatering, when the tree recovered from drought responses. The M four five soil sensor was installed after the first drought period, showed the decrease in soil water potential for the second drought period progressively, and returned to offset after second rewatering. As expected, the stem

Figure IV-three The Pictures of the Apple Tree Before and After Re-watering.

- less than span id equals "page-sixty-five to zero" greater than (a) Apple tree on Day twenty-two right before rewatering - temperature measured by the sensors increased during the day, and decreased at night. The following discussion covers detailed results from the G H four data. (b) Apple tree on Day twenty-four, two days after rewatering.

Figure IV-four (#page-sixty-six to zero) shows the three days when the Scholander pressure chamber data was taken together with that of the mu TMs.

Day seven \(Figure IV-four- (#page-sixty-six to zero)a) was during the first drought period before rewatering. The plant was experiencing large water stress. The Scholander measured a water potential of down to minus thirty bars, while the typical range observed in apple trees is minus fifteen to minus twenty bars. Therefore, the apple tree was experiencing large stress. The sensors were showing larger tensions than the Scholander (up to minus forty bars). There are two possible reasons for this: one) the micro T M was measuring real tension which was much higher than the coverage of the pressure chamber (zero to minus forty bar); two) during the

less than span id equals "page-sixty-six to zero" greater than Figure IV-four Comparison between Scholander Chamber and the Micro-Tensiometer The black line represents P one eight seven. The green line represents P two zero. The blue line represents P one seven six. The magenta line represents P one seven nine. The line colors are the same for all three subplots.

- (a) Day seven(a sunny day), the Scholander data were measured before rewatering. - (b) Day nine (a rainy day), two days after rewatering for the first drought period. - imposed drought, the sensors and tissue were separated by a larger vapor gap, and resulted in larger vapor psychrometric effect discussed above. (c) Day twenty-four (a sunny day), two days after the rewatering for the second drought period on a sunny day.

Day nine \(Figure IV-four- (#page-sixty-six to zero)b) was two days after rewatering for the first drought period, the P two zero, with e P T F E membrane, showed delayed response when the temperature was increasing, and advanced response when the temperature was dropping. These observations were expected if the P two zero was measuring the vapor psychrometric effect across the e P T F E membrane: when the temperature increases, the sharp decrease in measured water potential was observed. This observation can be explained by the "positive" psychrometric effect. It happens when the sensor has a slightly higher temperature than the tissue. The delayed response could be explained due to the time scale for heat conduction from the outside environment to the sensor. When the temperature decreases at night, the sensor is expected to have a slightly lower temperature than the tissue, the vapor condensates on the P o S i membrane, and results in the sharp increase in measured water potential ("negative" psychrometric effect). P one seven nine delayed its response in a similar way as P two zero. However, we expected the other sensors (P one eight seven, black curve, and P one seven six, blue curve), which responded faster than P two zero, to measure the real stem water potential. Therefore, we hypothesize that the P one seven nine was not in good contact with the tissue. Since the day nine was rainy, we expected that the plant did not have a full transpiration. Nevertheless, the plant should still respond to solar intensity and V P D. These expectations could explain varying stem water potential measured during the day. P one eight seven and P one seven six had the closest correlation with the Scholander pressure chamber, but were usually delayed for about zero point five to one hour. These differences observed for P one eight seven and P one seven six might be due to the systematic difference between the leaf stem water potential measured by the pressure chamber and the trunk stem water potential measured by the mu TMs, the vapor psychrometric effect, or the psychrometric effect specifically due to the xylem tissue in direct contact with the sensors; we favor the hypothesis of a psychrometric effect since the sensors were proved to be able to measure the osmotic potential of the sucrose solution within plus or minus two bars of accuracy \(Figure III-three\) (#page-fifty-one to one).

Day twenty-four \(Figure IV-four- (#page-sixty-six to zero)c) was on a sunny day without clouds, and was two days after rewatering for the second drought period. P one seven six started to read large tensions, about twenty bars more negative than the Scholander response; this observation suggests that P one seven six lost contact with the plant tissue. P one eight seven, on the other hand, showed good correlation with the Scholander response, in distinction from all the other sensors. However, when the day was approaching night, P one eight seven returned more quickly toward zero than the Scholander Pressure Chamber. The reason might be the accumulation of osmolites in leaves, which resulted in high osmotic potential. We expected the predawn water potential measured by the Scholander Pressure chamber may be the high osmotic potential discussed. Since the sensors were in direct contact with the tissue, the small molecules dissolved in xylem sap could get into the sensors, resulting in the insensitivity of the sensor to osmotic potential. At night, the osmolites inside the micro T M might cause the sensors to read positive pressure due to the opposite direction of diaphragm deflection.

When comparing the behavior of P one eight seven across the three figures in Figure IV-four, (#page-sixty-six to zero) the behavior of P one eight seven appeared to improve progressively during the month, when compared with the Scholander pressure chamber. The possible reasons for this improvement in P one eight seven could include: one) the wound response of the plant resulted in new tissue growing around the sensor, and improved the liquid and thermal contact between the sensor and the tissue; two) The embolized xylem elements around the sensor recovered from cavitation, and improved the sensor-tissue contact; and using a chisel to open a slit for sensor installation may have caused less damage to the plant than drilling a hole, because the other sensors installed in drilled holes appeared to progressively lose their contact with the tissue. However, it was still worth keeping the sensors inside the plant for a longer time to see how their behavior evolves over longer periods.

less than span id equals "page-sixty-nine to zero" greater than Figure IV-five Comparison of the mu TMs with delta T(minus fifteen min), Solar Radiation and Vapor Pressure Deficit - (a) Comparison of the mu TMs with T minus T at fifteen minutes prior. - (b) the mu TMs vs. Solar Radiation - (c) the mu TMs vs. V P D Figure IV-five (#page-sixty-nine to zero) shows the dependence of plant water potential on the delayed temperature difference \(Figure IV-five- (#page-sixty-nine to zero)a), solar intensity \(Figure IV-five- (#page-sixty-nine to zero)b) and vapor pressure deficit (V P D) \(Figure IV-five- (#page-sixty-nine to zero)c) on the same rainy day showed in Figure IV-four- (#page-sixty-six to zero)b. We selected this rainy day because the V P D and solar intensity varied more significantly than on a normal sunny day, and was helpful for the observation of the sensor response. It is worth noting that T minus T at fifteen minutes prior, V P D, solar intensity, and water potential measured by the sensors varied in a similar manner. It is hard to determine which one of the three major factors dominate on the variations of water potential.

Figure IV-five- (#page-sixty-nine to zero)a compared the sensor response to the "temperature difference", the fifteen min temperature difference estimation ( T minus T at fifteen minutes prior) mentioned above. The temperature data were calculated from P one seven six, due to its position in the center of the sensors installed on the tree.

less than span id equals "page-seventy to zero" greater than Figure IV-six Linear comparison between the Scholander data and the sensors.

- (a) Chronological Record on Day twenty-four with T minus T at fifteen minutes prior; - (b) mu TMs vs. Scholander Pressure Chamber. The sensor data were plotted against the Scholander data. The slopes and the quality of the correlation were shown for each sensor.

The sensor still showed a strong correlation with T minus T at fifteen minutes prior, as in the G H two results. This observation suggests that a psychrometric effect may have affected these measurements as well.

Figure IV-five- (#page-sixty-nine to zero)b compares mu TMs' response to solar intensity. The sensors had a better correspondence on the variations of solar intensity than the Scholander pressure chamber. In particular, in the region labelled by "i", we see a midday drop in the response of the sensors as the solar intensity dropped. We note though that T minus T at fifteen minutes prior also dropped during this period.

Figure IV-five- (#page-sixty-nine to zero)c shows the mu TMs' relationship to V P D. The V P D data were calculated based on the relative humidity and the temperature data from the Cornell Orchard Weather Station by assuming near-saturation vapor pressure inside the leaves. The labelled regions (i, ii and iii) in the plots showed that the midday water potential correlated better with the intensity of solar radiation, while the variations of the midday water potential correlated with V P D. For example, circle (ii) in Figure IV-five- (#page-sixty-nine to zero)c shows a correlation between the response of P one eight seven and the V P D variation.

Figure IV-six- (#page-seventy to zero)a compares the responses of the tensiometers to the delayed temperature difference ( delta)on day twenty-four when numerous bomb measurements were performed. The responses from P two zero, P one seven six and P one seven nine were similar, and may follow on the temperature difference, while P one eight seven had a similar trend as the Scholander pressure chamber data, even though the values were not exactly matched. P two zero read close to zero when the Scholander measured minus ten to minus fifteen bars of water potential. The Scholander responses reached plateau while the P two zero kept reading more and more negative water potential. Both P one seven six and P one seven nine had similar response as P two zero, but not as extreme. Therefore, we expected a linear regression if plot P one eight seven against the Scholander data.

Figure IV-six- (#page-seventy to zero)b presents the correlation between the mu TMs and the Scholander pressure chamber on day twenty-four. The sensor responses of the four mu TMs was plotted against the Scholander

less than span id equals "page-seventy-two to zero" greater than Figure IV-seven G H four--Second Drought Period The sensors were labeled in the same color as in previous plots.

data. P one eight seven had an almost linear correspondence with the Scholander data, and the best fitting quality ( R-squared equals zero point nine three), compared to R-squared approximately zero point eight zero of the other sensors.

Figure IV-seven (#page-seventy-two to zero) showed the complete data over the second drought period. The soil and stem water potential during a drought period was theoretically sketched in Figure II-three- (#page-twenty-one to one)a sixteen, and was tested experimentally by Gardner and Nieman in one thousand nine hundred sixty-four using a pepper plant \(Figure II-three- (#page-twenty-one to one)b). Compared to the literature, the data from my experiment indicated close soil and stem water potential at night when the soil was not under stress. During the drought period, the soil water potential was much less negative than the stem water potential at night, while the literature showed almost identical soil and leaf (stem) water potential when the pepper plant was under tension. The possible reasons were that the soil sensors were not installed deep enough to read the soil sample in direct contact with the roots. Another possibility was that the pathway from the soil to the sensor generated high hydraulic resistance during drought period fifty-nine. The high

less than span id equals "page-seventy-three to zero" greater than Figure IV-eight The Micro-Tensiometer in Soil resistance could be in the soil, the soil-root interface, or anywhere in the xylem upstream of the sensor. The generation of high hydraulic resistance requires further investigation. In addition, the root system of apples has very low density and are inconsistent in distribution. Therefore, the soil sensors may not have measured the soil water potential that is effective for the apple tree. The predawn Scholander pressure chamber measured a minus five bar water potential in region (ii), which was much more negative than the sensor data. Comparing regions (i) and (iv) for wellwatered conditions, we note that the offset change of the sensors was not significant after twelve days. This observation tends to support our decision to shift the sensor data to zero these predawn responses.

Figure IV-eight (#page-seventy-three to zero) shows the micro T M measurements in the soil. The micro T M reported diurnal variations of the soil water potential. However, we cannot completely exclude the temperature effects on the diurnal variations. These temperature effects include both the psychrometric effect and the temperature effect on the sensor signaling. Additionally, the micro T M showed a minus fourteen bar negative water potential at the end of the second drought period (day twenty-two). This tension was shown relaxed after the second rewatering on day twenty-two.

Combining the above results, the water potential measured by the micro T M showed strong dependence on the "temperature difference", solar intensity and V P D. It has also been shown that, several weeks after embedding, the P one eight seven had linear correlation with the Scholander pressure chamber. These observations led to the hypothesis that the sensor P one eight seven was measuring real tissue water potential. Further studies need to be done to test this hypothesis.

The P one eight seven, which was the bare device and should have had the best contact with the plant tissue, showed a linear correlation with the Scholander data after being embedded for almost one month inside an apple tree. P two zero had an e P T F E membrane between the plant tissue and the sensor. Therefore, P two zero has known vapor gap and works as an indicator for the psychrometric effect. If a micro T M behaved in a similar way as the P two zero, it suggests it has lost contact with the tissue.

The results of G H four give us preliminary evidence that the packaging strategy of P one eight seven worked better than other packaging strategies. Nevertheless, some observations were still able to guide us to further studies and hypotheses. Considering the sensors were placed at different heights on the tree, a gradient of water potential in the direction from lower positioned sensor to the higher positioned sensor was expected \(Figure IV-seven- (#page-seventy-two to zero)iii). However, no direction observation of this gradient existed based on our current data. Therefore, a hypothesis is that the radial water potential gradient dominates when the water stress level is low, due to the small difference in drilled depth for the sensors. Previous studies have shown radial and axial water potential gradient through a sap flow meter and measured radial hydraulic resistance in a cut wood stem in laboratory, but no direct measurements have been reported that tested for its existence.

less than span id equals "page-seventy-five to zero" greater than V. FUTURE WORK.

<break time="0.8s"/>

less than span id equals "page-seventy-five to one" greater than The Radial and Axial Water Potential Gradient in a Stem.

<break time="0.8s"/>

As discussed in Section IV.B, (#page-sixty-three to zero) one hypothesis is that differences between the micro T M readings and the bomb results from a radial gradient of tissue water potential within the stem. To test this hypothesis, we will choose a healthy apple tree in the Cornell Orchard with seven cm diameter (expecting five mm to twenty mm of active xylem).

Figure V-one (#page-seventy-six to zero)-a presents the experiment set-up for the above hypothesis. Six sensors will be divided into two groups. These two groups will be separated by thirty cm to forty cm from each other axially. For each group, three one point five mm x three mm diaphragm size mu TMs will be installed at three different depths (five mm, ten mm and fifteen mm). For each axial position, an additional sensor with e P T F E membrane will be installed at five mm depth to indicate vapor psychrometric effect, but was not shown in Figure V-one- (#page-seventy-six to zero)a. This diaphragm size balances the high sensitivity and short response time among all three types of sensors, as shown in Table III-one. (#page-fifty-two to zero) All sensors used will be packaged in the same way as P one eight seven, which means they will have wire-bonds protected and external wiring protection from external mechanical stress and corrosion. Identical sensors with similar characteristics will allow for easier comparison. All sensors will be installed at least one m above the soil. This distance from the ground minimizes temperature effects from the ground. The sensors will not be installed near branches due to their complex xylem structure in these regions. After installation, thermal insulation and reflective insulation will be added, as done in the greenhouse experiments.

Two one point five times three sensors will be installed deeply (about fifty cm) into the soil. This depth will help prevent the temperature variations in the air from affecting the soil water potential measurements, and help us get a near-root soil water potential as well.

The Scholander pressure chamber will still be used as the benchmark of the micro T M testing. The stem water potential will be measured in the same method as described in Section III.B.two.ii. (#page-fifty-four to one) One pyranometer will be positioned four m above the canopy of the tree to monitor the solar intensity. The V P D data will be obtained from the Cornell Orchard Weather Station. We will also add a relative humidity meter next to the tree for higher time-resolution monitoring.

Additionally, we will use a CIRUS-three to measure the photosynthetic rate of the tree through gas exchange analysis.

less than span id equals "page-seventy-six to zero" greater than Figure V-one Orchard and Growth Chamber Experiment Set-up Plan (a) The Schematic Diagram of the Orchard Experiment Plan for Radial and Axial Water Potential Gradient Testing. The sensors will be inserted into different radial depths and axial heights. The solar intensity will be monitored using a pyranometer. The soil sensors are not shown here.

(b) The Schematic Diagram of the Growth Chamber Plan for the study of vapor and tissue psychrometric effect, as well as the relationship between the stem water potential and the rate of transpiration. The soil sensors are not shown here.

We expect that all sensors will respond linearly with the Scholander pressure chamber, as shown for P one eight seven -micro T M in Figure IV-six. (#page-seventy to zero) For radial water potential, the expected result is a positive water potential gradient from outer xylem to inner xylem, which means outer xylem has more negative water potential than the inner part. Vertically, the sensors at a lower position should sense less negative water potential than the higher positioned sensors. When it comes to the rate of transpiration, a linear correlation is expected between the stem water potential and the rate of transpiration. We also expect the transpiration rate to be proportional to the solar intensity and the V P D.

less than span id equals "page-seventy-seven to zero" greater than Vapor and Tissue Psychrometric Effects Testing and the Study on Stomata Regulation.

<break time="0.8s"/>

Stomata opening and closing controls the rate of transpiration at a given V P D and solar intensity. With the high time-resolution micro T M, the factors affecting the stomata regulation could be studied. A growth chamber will be used to monitor the factors that affect the rate of transpiration accurately. Two healthy apple trees with three to four cm in diameter will be used for this experiment. Two sensors with the same diaphragm sizes (one point five mm x three mm) will be installed into each tree at five-mm-deep and ten-mm-deep, separated by less than ten cm, and at least one m above the soil. The third sensor will be installed right above the soil with ten-mm-deep. The sensors will be insulated with the standard method. The Scholander pressure chamber will be used to check whether the sensors have good thermal and tissue contact with the plant. Four factors will be controlled and monitored during the experiment: light intensity, relative humidity, temperature of the growth chamber, and the soil water content. Only one factor will be varied each time to test the correlation between the stem water potential and the varied factor and the response time of the plant. The light will be turned on and off diurnally for the normal growth of the plants, except when the light intensity is the variable. One micro T M (one point five mm x three mm) will be installed inside the soil for each plant for soil water potential monitoring.

The light intensity will first be varied by turning it on and off for two hour intervals alternatively, and then varied in a step change way, while keep the other factors constant and the soil saturated. The response of the plants will be monitored through the mu TMs. The expected response is that the stem water potential decreases (more negative) when the light is on, and increases back to soil water potential when the light is off. The correlation between the stepchange light intensity and the stem water potential should be linear.

To prevent possible vapor psychrometric effects on the sensors, the temperature will be kept constant while changing the relative humidity inside the growth chamber. The increased V P D will drive the evaporation from leaves to the atmosphere and generate more negative water potential. A linear regression between the V P D and the sensor reading is also expected.

The effects of soil water potential effects on the stomata regulation will be tested by controlling constant V P D and light intensity diurnally in the growth chamber while drying the soil progressively. Since the light intensity will be kept constant during the day, the change in the stem water potential due to the stomata opening and closing will be easily identified. After several days of drying, the soil will be re-watered and the response of the plants will be monitored.

The psychrometric effect on sensor will be studied by water the soil with ten degrees C water and insulate the soil with appropriate thermal insulation, while maintaining twenty-five degrees C growth chamber temperature. If the increase in water potential happens simultaneously for the three sensors on each tree, it means the lower sap temperature in the xylem results in a psychrometric effect. If the increase in water potential happens non-simultaneously, and the response happens in the order from five-cm-deep sensor, ten-cm-deep near root sensor and the ten-cm-deep stem sensor, that means the insulation is nearly ideal and tissue water potential is measured. An apple tree transpires water from the active xylem. Therefore, five-cm sensor is expected to be the first to experience tissue psychrometric effect, and the ten-cm stem sensor is expected to be the last.

less than span id equals "page-eighty to zero" greater than VI. CONCLUSION.

<break time="0.8s"/>

The development, installation and the in-plant testing of the second generation micro T M were presented in this thesis. The micro T M has been shown to be able to measure the plant stem water potential with high time-resolution, and was able to achieve a linear regression with the widely accepted Scholander pressure chamber data when being tested in plants.

The micro T M was built based on the M V L E theory by connecting the internal liquid to the outside vapor through a nano-scale porous silicon; this design combined the techniques of M E M S and piezo-resistive pressure sensing to transduce the energy signal to mechanical signal, and eventually to electronic signal.

Greenhouse experiment two (G H two) was conducted to develop the thermal insulation methods to minimize the thermal noise from the outside environment. From the G H two results, the sensors showed much more negative water potential than the pressure chamber measurements (about minus fifteen bar). The hypothesis about the existence of the vapor psychrometric effect due to the sensor-tissue vapor gap was proposed (seven point seven seven megapascals over degrees C) and was tested in the G H four experiment by trying different packaging strategies to improve the sensor-tissue thermal contact.

The G H four experiment showed one device P one eight seven with linear correlation with the Scholander pressure chamber. This device was a bare device, which has direct thermal contact with the tissue, and was installed with a minimal damage to the plant tissue. The gradual improvement in its measurement might be due to the growing of the wound tissue, or the reconnecting of the cavitated xylem elements around the sensor. The G H four also showed strong stem water potential dependence on solar intensity and vapor pressure deficit (V P D). Based on the G H four results, a new hypothesis about the axial and radial gradient of stem water potential will be tested in next step experiments.

The radial and axial stem water potential will be tested by inserting mu TMs at different depths of the stem to test whether there is a gradient of water potential exist. The psychrometric effect and the stem water potential dependence on V P D and solar intensity will be further studied in growth chamber experiments. Further work will be done to generate a well-developed sensor application strategy for both research and commercial applications.

Current results proved that a micro T M could be used to monitor water potential in real-time with high accuracy. The mu TMs can be integrated into water monitoring systems of agriculture to improve water use efficiency and water use productivity. They can also be used to conduct plant drought response studies, and to screen for drought tolerant phenotypes of genetic modified plants. Furthermore, monitoring the water stress using the mu TMs in forests can help predict the global climate change.

less than span id equals "page-eighty-two to zero" greater than VII. REFERENCES.

<break time="0.8s"/>

- sixty-two. Buckingham E. Studies On The Movement of Soil Moisture. Statew Agric L Use Baseline two thousand fifteen. one thousand nine hundred seven;one. doi:ten point one zero one seven over CBO nine seven eight one one zero seven four one five three two four.four. - sixty-three. Gardner WR, Nieman RH. Lower Limit of Water Availability to Plants. Science (eighty-). one thousand nine hundred sixty-four;one hundred forty-three(three thousand six hundred thirteen):one thousand four hundred sixty to one thousand four hundred sixty-two. doi:ten point one one two six over science..three thousand six hundred thirteen point one four six zero. - sixty-four. Pagay V, Santiago M, Sessoms D a, and others A microtensiometer capable of measuring water potentials below minus ten megapascals. Lab Chip. two thousand fourteen;fourteen(fifteen):two thousand eight hundred six to two thousand eight hundred seventeen. doi:ten point one zero three nine over c four lc zero zero three four two j.

less than span id equals "page-eighty-nine to zero" greater than VIII. APPENDIX.

<break time="0.8s"/>

less than span id equals "page-eighty-nine to one" greater than Masks Designed for Micro-Tensiometer Fabrication.

<break time="0.8s"/>

Tensiometer CAD.

Changed three masks:.

<break time="0.8s"/>

- one. Cavity more conservative vein pattern (pitch equals one hundred ten microns), added numbers, removed rulers. - two. Polysilicon longer & narrower piezoresistors, polysilicon goes under all bridge wires over pads (not P R T wires). R equals two thousand ohms five hundred ohms for better fit in current mask. - three. Platinum changed configuration in piezoresistors to fit longer resistors and improve 'zero'.

New piezoresistors are longer, slightly narrower (previous: twenty micron, new: fifteen micron), and have lower resistance (R equals two thousand ohms five hundred ohms)

one mm Notice polysilicon goes under all bridge-connected metal.

Section one point five, mm.

<break time="0.8s"/>

two mm

three point five mm.

<break time="0.8s"/>

two mm two WB

less than span id equals "page-ninety-five to zero" greater than G H two DATALOGGING PROGRAM.

<break time="0.8s"/>

less than span id equals "page-ninety-eight to zero" greater than G H four DATALOGGING PROGRAM.

<break time="0.8s"/>

less than span id equals "page-one hundred four to zero" greater than G H four Data Analysis Program.

<break time="0.8s"/>

less than span id equals "page-one hundred eleven to zero" greater than two D HEAT TRANSFER SIMULATION PROGRAM.

<break time="0.8s"/>

This concludes In-plant applications of a micro-tensiometer water stress sensor.